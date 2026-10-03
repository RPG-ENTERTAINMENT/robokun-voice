"""Thumbnail (1280x720) for a long episode: clean frame of the 'love' beat + title."""
import sys, os, json
sys.path.insert(0, 'eng')
from engine_l import Ep, A
from PIL import Image, ImageDraw, ImageFont
ep, vo, out = sys.argv[1:4]
s = Ep(json.load(open(ep)), vo); e = s.ep['beats']
cand = [k for k, b in enumerate(e) if b.get('robo', {}).get('pose') == 'love' and 'say' not in b] or [len(e)-1]
t = s.beats[cand[0]]['t0']+1.4
im = Image.fromarray(s.render(t)).convert('RGB').resize((1280, 720), Image.LANCZOS)
d = ImageDraw.Draw(im); f = ImageFont.truetype(A+'fonts/hmp.ttf', 96); f2 = ImageFont.truetype(A+'fonts/hmp.ttf', 48)
def T(y, txt, ft, sw):
    w = ft.getbbox(txt)[2]; d.text(((1280-w)//2, y), txt, font=ft, fill=(255, 251, 240), stroke_width=sw, stroke_fill=(110, 82, 60))
T(40, s.ep['title'], f, 12); T(610, 'ロボしず ・ ちょっと ながい おはなし', f2, 8)
im.save(out); print('thumb', out, t)
