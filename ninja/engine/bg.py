"""NINJA DIGITAL BAR の背景（1080x1920）を作る。静止部分は1回だけ作り、デジタルウォールの中身は毎フレーム動かす。"""
import numpy as np, math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
WALL = (70, 300, 1010, 900)      # デジタルアートの壁（動く）
COUNTER_Y = 1190                 # カウンター上端
FLOOR_Y = 1360                   # 床の始まり


def _glow(layer, radius):
    return layer.filter(ImageFilter.GaussianBlur(radius))


def static_bg(font_path):
    rnd = random.Random(7)
    base = Image.new('RGB', (W, H))
    a = np.zeros((H, W, 3), np.float32)
    y = np.linspace(0, 1, H)[:, None]
    a[..., 0] = 14 + 10 * (1 - y)
    a[..., 1] = 7 + 4 * (1 - y)
    a[..., 2] = 34 + 20 * (1 - y)
    base = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(base)
    # 和柄（青海波）を壁にうっすら
    pat = Image.new('L', (W, H), 0)
    pd = ImageDraw.Draw(pat)
    for row in range(0, 1200, 40):
        for col in range(-40, W + 40, 80):
            cx = col + (40 if (row // 40) % 2 else 0)
            for r in (36, 26, 16):
                pd.arc((cx - r, row - r + 40, cx + r, row + r + 40), 180, 360, fill=255, width=2)
    base = Image.composite(Image.new('RGB', (W, H), (70, 40, 120)), base, pat.point(lambda v: int(v * 0.10)))
    d = ImageDraw.Draw(base)
    # 天井のスポットライト
    light = Image.new('RGB', (W, H), 0)
    ld = ImageDraw.Draw(light)
    for i, x in enumerate((180, 540, 900)):
        col = [(255, 90, 180), (90, 220, 255), (255, 90, 180)][i]
        ld.polygon([(x - 18, 0), (x + 18, 0), (x + 230, 1350), (x - 230, 1350)], fill=tuple(c // 6 for c in col))
        ld.ellipse((x - 26, -14, x + 26, 22), fill=(255, 255, 240))
    light = _glow(light, 30)
    base = Image.fromarray(np.minimum(255, np.array(base, np.int32) + np.array(light, np.int32)).astype(np.uint8))
    d = ImageDraw.Draw(base)
    # 看板「NINJA DIGITAL BAR」（ネオン）
    sign = Image.new('RGB', (W, H), 0)
    sd = ImageDraw.Draw(sign)
    f = ImageFont.truetype(font_path, 74)
    txt = [('NINJA ', (255, 255, 255)), ('DIGITAL ', (255, 61, 139)), ('BAR', (255, 255, 255))]
    tw = sum(sd.textlength(t, font=f) for t, _ in txt)
    x = (W - tw) / 2
    for t, c in txt:
        sd.text((x, 150), t, font=f, fill=c)
        x += sd.textlength(t, font=f)
    glow = _glow(sign, 14)
    base = Image.fromarray(np.minimum(255, np.array(base, np.int32) + (np.array(glow, np.int32) * 1.6).astype(np.int32) + np.array(sign, np.int32) // 2).astype(np.uint8))
    d = ImageDraw.Draw(base)
    # 壁の金の額縁
    x0, y0, x1, y1 = WALL
    d.rounded_rectangle((x0 - 18, y0 - 18, x1 + 18, y1 + 18), 26, fill=(20, 12, 30), outline=(212, 170, 80), width=6)
    d.rounded_rectangle((x0 - 6, y0 - 6, x1 + 6, y1 + 6), 20, outline=(120, 90, 40), width=2)
    # 後ろの棚（光るボトル）
    for si, sy in enumerate((955, 1075)):
        d.rectangle((40, sy + 88, W - 40, sy + 98), fill=(140, 100, 50))
        n = 13
        for i in range(n):
            bx = 70 + i * (W - 140) / n + rnd.randint(-6, 6)
            bh = rnd.randint(52, 86)
            bw = rnd.randint(26, 36)
            col = rnd.choice([(255, 80, 120), (80, 220, 255), (255, 200, 80), (170, 110, 255), (90, 255, 170)])
            top = sy + 88 - bh
            d.rounded_rectangle((bx, top + 18, bx + bw, sy + 88), 7, fill=tuple(int(c * 0.55) for c in col))
            d.rectangle((bx + bw * 0.35, top, bx + bw * 0.65, top + 20), fill=tuple(int(c * 0.45) for c in col))
            d.rectangle((bx + 5, top + 26, bx + 9, sy + 80), fill=tuple(min(255, int(c * 0.95)) for c in col))
    # 棚の下のネオン
    neon = Image.new('RGB', (W, H), 0)
    nd_ = ImageDraw.Draw(neon)
    nd_.rectangle((40, 1053, W - 40, 1057), fill=(255, 61, 139))
    nd_.rectangle((40, 1173, W - 40, 1177), fill=(56, 217, 255))
    # カウンター
    d.rectangle((0, COUNTER_Y, W, FLOOR_Y), fill=(36, 18, 22))
    for i in range(0, W, 6):
        v = 30 + int(10 * math.sin(i * 0.05) + 6 * math.sin(i * 0.23))
        d.line((i, COUNTER_Y + 24, i + 30, FLOOR_Y), fill=(v + 14, v // 2 + 4, v // 2), width=3)
    d.rectangle((0, COUNTER_Y, W, COUNTER_Y + 22), fill=(212, 170, 80))
    d.rectangle((0, COUNTER_Y + 22, W, COUNTER_Y + 28), fill=(110, 80, 30))
    nd_.rectangle((0, FLOOR_Y - 10, W, FLOOR_Y - 4), fill=(255, 61, 139))
    glow = _glow(neon, 10)
    base = Image.fromarray(np.minimum(255, np.array(base, np.int32) + np.array(glow, np.int32) * 2 + np.array(neon, np.int32)).astype(np.uint8))
    d = ImageDraw.Draw(base)
    # 床（つやのある黒＋反射）
    fl = np.array(base, np.float32)
    fy = np.arange(FLOOR_Y, H)
    t = (fy - FLOOR_Y) / (H - FLOOR_Y)
    fl[FLOOR_Y:, :, 0] = (16 + 6 * t)[:, None]
    fl[FLOOR_Y:, :, 1] = (10 + 4 * t)[:, None]
    fl[FLOOR_Y:, :, 2] = (28 + 10 * t)[:, None]
    refl = np.array(base, np.float32)[FLOOR_Y - 1:FLOOR_Y - 1 - (H - FLOOR_Y):-1]
    if refl.shape[0] == H - FLOOR_Y:
        fl[FLOOR_Y:] += refl * (0.28 * (1 - t))[:, None, None]
    base = Image.fromarray(fl.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(base)
    for k in range(1, 9):  # 床の目地（遠近）
        yy = FLOOR_Y + int((H - FLOOR_Y) * (k / 9) ** 1.6)
        d.line((0, yy, W, yy), fill=(40, 26, 60), width=2)
    for k in range(-8, 9):
        d.line((W / 2 + k * 40, FLOOR_Y, W / 2 + k * 260, H), fill=(40, 26, 60), width=2)
    # 提灯（左右）
    lan = Image.new('RGB', (W, H), 0)
    ld = ImageDraw.Draw(lan)
    for cx in (40, W - 40):
        ld.line((cx, 0, cx, 250), fill=(80, 60, 30), width=3)
        ld.ellipse((cx - 34, 250, cx + 34, 360), fill=(230, 60, 50))
        for yy in range(262, 352, 14):
            ld.line((cx - 30, yy, cx + 30, yy), fill=(170, 40, 30), width=2)
    base.paste(lan, (0, 0), lan.convert('L').point(lambda v: 255 if v > 10 else 0))
    lg = _glow(lan, 24)
    base = Image.fromarray(np.minimum(255, np.array(base, np.int32) + np.array(lg, np.int32)).astype(np.uint8))
    return base


class Wall:
    """デジタルアートの壁：毎フレーム色が流れるプラズマ＋流れる光の粒"""
    def __init__(self):
        x0, y0, x1, y1 = WALL
        self.w, self.h = (x1 - x0) // 4, (y1 - y0) // 4
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        self.xx, self.yy = xx / self.w, yy / self.h
        rr = np.hypot(self.xx - 0.5, self.yy - 0.5)
        self.rr = rr
        m = np.clip(1 - np.maximum(0, rr - 0.42) * 6, 0, 1)
        self.mask = m

    def frame(self, t, boost=0.0, tint=None):
        xx, yy = self.xx, self.yy
        v = (np.sin(xx * 9 + t * 1.3) + np.sin(yy * 7 - t * 1.1) + np.sin((xx + yy) * 6 + t * 0.9)
             + np.sin(self.rr * 14 - t * 2.2)) / 4
        # 等高線をネオンの線にする（黒地に光る流れる線）
        k = (v * 5 + t * 0.6) % 1.0
        line = np.exp(-((k - 0.5) ** 2) / 0.004)
        hue = (xx * 0.8 + yy * 0.5 + t * 0.08) % 1.0
        r = 0.5 + 0.5 * np.cos(6.283 * (hue + 0.0))
        g = 0.5 + 0.5 * np.cos(6.283 * (hue + 0.33))
        b = 0.5 + 0.5 * np.cos(6.283 * (hue + 0.66))
        col = np.stack([r * 0.9 + 0.3, g * 0.6 + 0.1, b * 0.9 + 0.3], -1)
        base = np.stack([0.05 + 0.06 * (1 - yy), 0.02 + 0.02 * xx, 0.10 + 0.08 * yy], -1)
        img = base + col * line[..., None] * (0.9 + boost) + col * 0.08 * (0.5 + 0.5 * v[..., None])
        if tint is not None:
            img = img * 0.4 + np.array(tint, np.float32)[None, None] / 255 * 0.6 * (0.6 + boost)
        img = (img * 255).clip(0, 255).astype(np.uint8)
        x0, y0, x1, y1 = WALL
        return Image.fromarray(img).resize((x1 - x0, y1 - y0), Image.BILINEAR)
