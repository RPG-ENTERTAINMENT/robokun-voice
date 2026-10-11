"""Cut the extra ロボしず poses out of the 2026-10-11 character sheet (ロボットしずく 1536x1024),
upscale them x4 with Real-ESRGAN (anime 6B, CPU) and write assets/sp/<pose>.png.

The sheet is found automatically: any *.png in the repo root (or sprites/) that looks like it.
Skips quietly if the sheet has not been uploaded yet. Outputs are cached in vv/hq_sp/ (workflow cache).
"""
import os, sys, glob, shutil, subprocess
import numpy as np, cv2
from PIL import Image

OUT = 'assets/sp'
CACHE = 'vv/hq_sp'
VERSION = '1'
# pose name: (x0, y0, x1, y1) on the 1536x1024 sheet, labels excluded
BOX = {
    'side_r': (143, 160, 263, 332), 'side_l': (262, 160, 380, 332), 'sit': (742, 165, 865, 332),
    'run': (14, 428, 166, 565), 'jump': (176, 420, 306, 565), 'tumble': (314, 425, 472, 565), 'getup': (688, 420, 826, 565),
    'wave': (16, 600, 146, 748), 'pompom': (143, 605, 266, 748), 'clap': (364, 600, 470, 748), 'heart': (590, 598, 706, 748),
    'dash': (702, 600, 848, 748),
    'coffee': (868, 440, 982, 575), 'book': (993, 445, 1108, 575), 'music': (1110, 420, 1252, 575),
    'phone': (1260, 445, 1378, 575), 'sweep': (1383, 420, 1516, 575),
    'cook': (998, 600, 1124, 735), 'present': (1122, 598, 1226, 735),
    'hug_inu': (1243, 610, 1400, 737), 'hug_neko': (1390, 610, 1522, 737),
}
SCALE = 1.1   # match the size of the existing sp/*.png sprites
PROBES = [((1050, 92), (237, 154, 176)), ((60, 132), (178, 212, 247)), ((200, 808), (151, 130, 179))]
# used only until the sheet is uploaded, so episodes that name a new pose never crash the render
FALLBACK = {'side_r': 'wr1', 'side_l': 'wl1', 'sit': 'idle', 'run': 'd1', 'jump': 'j1', 'tumble': 'fall', 'getup': 'surprise',
            'wave': 'win', 'pompom': 'cheer', 'clap': 'joy', 'heart': 'love', 'dash': 'd2', 'coffee': 'smile', 'book': 'think',
            'music': 'closed', 'phone': 'think', 'sweep': 'idle', 'cook': 'smile', 'present': 'joy', 'hug_inu': 'love', 'hug_neko': 'love'}
WEIGHTS = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth'


def rrdbnet(path):
    """Real-ESRGAN RRDBNet (x4, 6 blocks), same layout as basicsr's, without extra dependencies."""
    import torch, torch.nn as nn, torch.nn.functional as F

    class RDB(nn.Module):
        def __init__(s, f=64, g=32):
            super().__init__()
            s.conv1 = nn.Conv2d(f, g, 3, 1, 1); s.conv2 = nn.Conv2d(f+g, g, 3, 1, 1); s.conv3 = nn.Conv2d(f+2*g, g, 3, 1, 1)
            s.conv4 = nn.Conv2d(f+3*g, g, 3, 1, 1); s.conv5 = nn.Conv2d(f+4*g, f, 3, 1, 1); s.lr = nn.LeakyReLU(0.2, True)
        def forward(s, x):
            x1 = s.lr(s.conv1(x)); x2 = s.lr(s.conv2(torch.cat((x, x1), 1))); x3 = s.lr(s.conv3(torch.cat((x, x1, x2), 1)))
            x4 = s.lr(s.conv4(torch.cat((x, x1, x2, x3), 1))); x5 = s.conv5(torch.cat((x, x1, x2, x3, x4), 1))
            return x5*0.2+x

    class RRDB(nn.Module):
        def __init__(s):
            super().__init__(); s.rdb1, s.rdb2, s.rdb3 = RDB(), RDB(), RDB()
        def forward(s, x): return s.rdb3(s.rdb2(s.rdb1(x)))*0.2+x

    class Net(nn.Module):
        def __init__(s, nb=6, f=64):
            super().__init__()
            s.conv_first = nn.Conv2d(3, f, 3, 1, 1); s.body = nn.Sequential(*[RRDB() for _ in range(nb)])
            s.conv_body = nn.Conv2d(f, f, 3, 1, 1); s.conv_up1 = nn.Conv2d(f, f, 3, 1, 1); s.conv_up2 = nn.Conv2d(f, f, 3, 1, 1)
            s.conv_hr = nn.Conv2d(f, f, 3, 1, 1); s.conv_last = nn.Conv2d(f, 3, 3, 1, 1); s.lr = nn.LeakyReLU(0.2, True)
        def forward(s, x):
            fe = s.conv_first(x); fe = fe+s.conv_body(s.body(fe))
            fe = s.lr(s.conv_up1(F.interpolate(fe, scale_factor=2, mode='nearest')))
            fe = s.lr(s.conv_up2(F.interpolate(fe, scale_factor=2, mode='nearest')))
            return s.conv_last(s.lr(s.conv_hr(fe)))

    sd = torch.load(path, map_location='cpu', weights_only=True)
    sd = sd.get('params_ema', sd.get('params', sd))
    m = Net(); m.load_state_dict(sd, strict=True); return m.eval()


def find_sheet():
    for f in sorted(glob.glob('*.png') + glob.glob('sprites/*.png')):
        try:
            im = Image.open(f).convert('RGB')
        except Exception:
            continue
        if abs(im.width/im.height - 1.5) > 0.02: continue
        a = np.asarray(im.resize((1536, 1024), Image.LANCZOS)).astype(int)
        if all(np.abs(a[y-3:y+4, x-3:x+4].reshape(-1, 3).mean(0)-c).mean() < 25 for (x, y), c in PROBES):
            return f, a.astype(np.uint8)
    return None, None


def lowres_alpha(c):
    c = c.astype(np.int16)
    cand = ((c.min(2) >= 250) & (c.max(2)-c.min(2) <= 3)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=4)
    h, w = cand.shape; bg = np.zeros_like(cand)
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        if x == 0 or y == 0 or x+ww == w or y+hh == h or a >= 400: bg[lab == i] = 1
    fg = 1-bg
    mn = c.min(2)
    for _ in range(2):   # peel the light speckle fringe left by the sheet's compression noise
        peel = (fg == 1) & (cv2.dilate(1-fg, np.ones((3, 3), np.uint8)) == 1) & (mn >= 236)
        fg[peel] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    keep = np.zeros_like(fg); big = st[1:, 4].max()
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        edge = x == 0 or y == 0 or x+ww == w or y+hh == h
        if a < 60 and mn[lab == i].mean() > 215: continue
        if a >= 0.08*big or (not edge and a >= 6) or (edge and a >= 0.01*big): keep[lab == i] = 1
    return keep.astype(np.float32)


def main():
    f, sheet = find_sheet()
    if f is None:
        for k, src in FALLBACK.items():
            if not os.path.exists(f'{OUT}/{k}.png') and os.path.exists(f'{OUT}/{src}.png'): shutil.copy(f'{OUT}/{src}.png', f'{OUT}/{k}.png')
        print('hq_sprites: sheet not uploaded yet -> fallback poses'); return
    stamp = f'{CACHE}/done_{VERSION}'
    if not os.path.exists(stamp):
        import torch
        os.makedirs(CACHE, exist_ok=True)
        wp = 'vv/anime6b.pth'
        if not os.path.exists(wp): subprocess.run(['curl', '-sSL', '-o', wp, WEIGHTS], check=True)
        model = rrdbnet(wp)
        torch.set_num_threads(max(os.cpu_count() or 2, 2))
        for k, (x0, y0, x1, y1) in BOX.items():
            c = sheet[y0:y1, x0:x1]
            a = lowres_alpha(c)
            cp = cv2.copyMakeBorder(c, 8, 8, 8, 8, cv2.BORDER_REPLICATE)
            t = torch.from_numpy(cp.astype(np.float32)/255.).permute(2, 0, 1)[None]
            with torch.no_grad(): u = model(t)[0].clamp(0, 1).permute(1, 2, 0).numpy()
            u = (u*255+0.5).astype(np.uint8)[32:-32, 32:-32]
            A4 = cv2.resize(a, (u.shape[1], u.shape[0]), interpolation=cv2.INTER_CUBIC)
            A4 = np.clip((A4-0.62)*2.4+0.5, 0, 1)
            A4 = cv2.erode(A4, np.ones((5, 5), np.uint8))
            A4 = cv2.GaussianBlur(A4, (0, 0), 0.9)
            rgba = np.dstack([u, (A4*255).astype(np.uint8)])
            ys, xs = np.where(rgba[..., 3] > 10)
            rgba = rgba[max(ys.min()-8, 0):ys.max()+9, max(xs.min()-8, 0):xs.max()+9]
            im = Image.fromarray(rgba)
            im = im.resize((round(im.width*SCALE), round(im.height*SCALE)), Image.LANCZOS)
            im.save(f'{CACHE}/{k}.png')
            print('hq_sprites', k, im.size, flush=True)
        open(stamp, 'w').write(f)
    os.makedirs(OUT, exist_ok=True)
    for p in glob.glob(f'{CACHE}/*.png'):
        shutil.copy(p, OUT)
    print('hq_sprites: installed', len(glob.glob(f'{CACHE}/*.png')), 'poses from', f)


if __name__ == '__main__':
    main()
