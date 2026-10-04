"""Designed YouTube thumbnail (1280x720) for a landscape episode.
Left: title panel. Right: the best emotional frame, cropped around ロボしず and ハナ.
usage: thumb_long.py EP.json VO_DIR OUT.png [episode_no]"""
import sys, os, json, math
sys.path.insert(0, 'eng')
from engine_l import Ep, A
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
ep_path, vo, out = sys.argv[1:4]; no = str(int(sys.argv[4])) if len(sys.argv) > 4 and sys.argv[4].isdigit() else ''
s = Ep(json.load(open(ep_path)), vo); e = s.ep['beats']; n = len(e)
GOOD = {'love': 3.6, 'joy': 3.4, 'win': 3.2, 'surprise': 3.0, 'cheer': 3.0, 'shy': 2.8, 'smile': 2.5}
best, bscore = 0, -9
for k, b in enumerate(e):
    r = b.get('robo') or {}; pose = s.beats[k]['pose']
    sc = GOOD.get(pose, 0)
    if b.get('cam') in ('close', 'mid'): sc += 1.2
    if b.get('fx'): sc += 1.5
    if 'say' not in b: sc += 1
    if r.get('do'): sc -= 4
    if b.get('card'): sc -= 4
    if 0.3 < k / n < 0.93: sc += 1
    if sc > bscore: best, bscore = k, sc
t = s.beats[best]['t0'] + (1.0 if 'say' not in e[best] else 0.08)
fr = Image.fromarray(s.render(t)).convert('RGB')
cx, cy, z = s.camera(t); rx = s.robot(t)['x']
def sx(x): return (x - cx) * z + 960
mid = (sx(rx) + sx(s.FL_X)) / 2 if s.hana_on else sx(rx)
cw, ch = 1152, 1080; x0 = int(min(max(mid - cw / 2, 0), 1920 - cw))
pic = fr.crop((x0, 0, x0 + cw, ch)).resize((768, 720), Image.LANCZOS)
pic = ImageEnhance.Color(ImageEnhance.Brightness(pic).enhance(1.12)).enhance(1.12)
W, H, PW = 1280, 720, 512
im = Image.new('RGB', (W, H), (255, 246, 226))
im.paste(pic, (PW, 0))
# torn-paper edge between panel and picture
edge = Image.new('L', (W, H), 0); de = ImageDraw.Draw(edge)
pts = [(PW + 18 + 10 * math.sin(y / 23.0) + 6 * math.sin(y / 7.3), y) for y in range(0, H + 1, 6)]
de.polygon([(0, 0)] + pts + [(0, H)], fill=255)
edge = edge.filter(ImageFilter.GaussianBlur(1.2))
panel = Image.new('RGB', (W, H), (255, 246, 226)); dp = ImageDraw.Draw(panel)
for i in range(0, H, 4): dp.line([(0, i), (PW + 40, i)], fill=(255, 246 - (i % 16 == 0) * 4, 226 - (i % 16 == 0) * 6))
shadow = edge.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45))
im = Image.composite(Image.new('RGB', (W, H), (90, 64, 44)), im, shadow.transform(shadow.size, Image.AFFINE, (1, 0, -8, 0, 1, 0)))
im = Image.composite(panel, im, edge)
d = ImageDraw.Draw(im)
FT = A + 'fonts/hmp.ttf'
def font(sz): return ImageFont.truetype(FT, sz)
# title lines
words = s.ep['title'].split(' ')
lines, cur = [], ''
for w in words:
    if cur and len((cur + w)) > 5: lines.append(cur); cur = w
    else: cur = (cur + w)
lines.append(cur); lines = lines[:3]
size = 150
while size > 60 and max(font(size).getbbox(l)[2] for l in lines) > PW - 70: size -= 4
lh = int(size * 1.18); total = lh * len(lines)
y = (H - total) // 2 + 10
for l in lines:
    f = font(size); w = f.getbbox(l)[2]; x = (PW - w) // 2 + 4
    d.text((x + 5, y + 7), l, font=f, fill=(206, 182, 150), stroke_width=12, stroke_fill=(206, 182, 150))
    d.text((x, y), l, font=f, fill=(104, 70, 46), stroke_width=12, stroke_fill=(255, 255, 255))
    y += lh
# ribbon top-left
rb = Image.new('RGBA', (300, 82), (0, 0, 0, 0)); dr = ImageDraw.Draw(rb)
dr.rounded_rectangle([0, 0, 299, 81], 24, fill=(255, 205, 64, 255), outline=(104, 70, 46, 255), width=5)
f2 = font(46); lab = '8ぷんアニメ'; dr.text(((300 - f2.getbbox(lab)[2]) // 2, 12), lab, font=f2, fill=(104, 70, 46))
rb = rb.rotate(-4, expand=True, resample=Image.BICUBIC); im.paste(rb, (34, 26), rb)
# badge bottom-left
lab = 'ロボしず' + (f' だい{no}わ' if no else '')
f3 = font(40); bw = f3.getbbox(lab)[2] + 56
bd = Image.new('RGBA', (bw, 72), (0, 0, 0, 0)); db = ImageDraw.Draw(bd)
db.rounded_rectangle([0, 0, bw - 1, 71], 36, fill=(120, 168, 92, 255))
db.text((28, 10), lab, font=f3, fill=(255, 252, 240))
im.paste(bd, ((PW - bw) // 2, H - 100), bd)
im.save(out); print('thumb', out, 'beat', best, 'pose', s.beats[best]['pose'], 't', round(t, 2))
