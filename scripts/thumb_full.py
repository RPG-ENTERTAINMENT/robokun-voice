"""YouTube thumbnail (1280x720) for a landscape episode, in the style of the very first long video:
the whole scene fills the picture, the title sits big in the middle at the top, and
"ロボしず ・ ちょっと ながい おはなし" runs along the bottom. No side panel.
The frame is the best emotional moment (same scoring as thumb_long.py), zoomed a little
towards ロボしず and the partner so they read well at small sizes.
usage: thumb_full.py EP.json VO_DIR OUT.png [episode_no]"""
import sys, json
sys.path.insert(0, 'eng')
from engine_l import Ep, A
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
ep_path, vo, out = sys.argv[1:4]
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
fr = Image.fromarray(s.render(t)).convert('RGB')          # 1920x1080
# zoom ~1.05x around the characters, anchored at the top so heads stay clear of the title
cx, cy, z = s.camera(t); rx = s.robot(t)['x']
def sx(x): return (x - cx) * z + 960
mid = (sx(rx) + sx(s.FL_X)) / 2 if s.hana_on else sx(rx)
cw, ch = 1830, 1029; x0 = int(min(max(mid - cw / 2, 0), 1920 - cw)); y0 = 0
im = fr.crop((x0, y0, x0 + cw, y0 + ch)).resize((1280, 720), Image.LANCZOS)
im = ImageEnhance.Color(ImageEnhance.Brightness(im).enhance(1.08)).enhance(1.12)
d = ImageDraw.Draw(im)
FT = A + 'fonts/hmp.ttf'
def font(sz): return ImageFont.truetype(FT, sz)
def T(y, txt, size, sw, maxw):
    while size > 40 and font(size).getbbox(txt)[2] > maxw: size -= 4
    f = font(size); w = f.getbbox(txt)[2]; x = (1280 - w) // 2
    d.text((x + 4, y + 6), txt, font=f, fill=(90, 64, 44), stroke_width=sw, stroke_fill=(90, 64, 44))   # soft drop
    d.text((x, y), txt, font=f, fill=(255, 251, 240), stroke_width=sw, stroke_fill=(110, 82, 60))
T(26, s.ep['title'], 108, 13, 1180)
T(628, 'ロボしず ・ ちょっと ながい おはなし', 50, 9, 1180)
im.save(out); print('thumb', out, 'beat', best, 'pose', s.beats[best]['pose'], 't', round(t, 2))
