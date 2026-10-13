"""Slide (panel 1240x780) generator for the インスタ講座 lesson videos.
make(spec, path) draws one slide from a small JSON spec. Also builds the classroom background and an original lo-fi BGM."""
import os, math, random, wave, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('IGC_SPRITES', os.path.join(HERE, '..', 'assets', 'sp'))
PHOTOS = os.environ.get('IGC_PHOTOS', os.path.join(HERE, '..', 'tests', 'img', 'edu001'))
def _font(*names):
    for n in names:
        for p in glob.glob(f'/usr/share/fonts/**/{n}', recursive=True): return p
    raise SystemExit('font missing: ' + names[0])
BLK = _font('NotoSansCJK-Black.ttc'); BLD = _font('NotoSansCJK-Bold.ttc')
EMOJI = _font('NotoColorEmoji.ttf')
EMO = ImageFont.truetype(EMOJI, 109)
def F(p, s): return ImageFont.truetype(p, s, index=0)
PW, PH = 1240, 780
NAVY = (10, 40, 100); PINK = (232, 72, 140); ORANGE = (247, 140, 50); PURPLE = (140, 70, 210); GREEN = (6, 170, 90); RED = (229, 72, 77); BLUE = (40, 120, 230)
CARD_COLS = [PINK, ORANGE, PURPLE, GREEN, BLUE, RED]
IGG = [(254, 218, 117), (250, 126, 30), (214, 41, 118), (150, 47, 191), (79, 91, 213)]
BGS = [((255, 236, 244), (232, 240, 255)), ((255, 244, 228), (255, 230, 236)), ((236, 250, 244), (255, 244, 230)), ((250, 240, 255), (236, 246, 255)), ((255, 248, 230), (240, 236, 255))]

_EC = {}
def emoji(ch, size):
    key = (ch, size)
    if key not in _EC:
        im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        try: ImageDraw.Draw(im).text((0, 0), ch, font=EMO, embedded_color=True)
        except Exception: pass
        bb = im.getbbox()
        if not bb: _EC[key] = Image.new('RGBA', (size, size), (0, 0, 0, 0)); return _EC[key]
        im = im.crop(bb); s = size / max(im.size)
        _EC[key] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return _EC[key]

def grad(w, h, cols):
    y, x = np.mgrid[0:h, 0:w]; t = (x / w + y / h) / 2; n = len(cols) - 1
    i = np.minimum(n - 1, (t * n).astype(int)); u = (t * n - i)[..., None]
    c = np.array(cols, dtype=float); out = c[i] * (1 - u) + c[i + 1] * u
    return Image.fromarray(out.astype(np.uint8), 'RGB')

def pastel(seed=0):
    c1, c2 = BGS[seed % len(BGS)]
    im = grad(PW, PH, [c1, c2]).convert('RGBA'); d = ImageDraw.Draw(im); rnd = random.Random(seed)
    for _ in range(26):
        x, y, r = rnd.randint(0, PW), rnd.randint(0, PH), rnd.randint(6, 18)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 150))
    return im

def sprite(name, h):
    im = Image.open(os.path.join(SP, name + '.png' if os.path.exists(os.path.join(SP, name + '.png')) else name + '.webp')).convert('RGBA'); s = h / im.height
    return im.resize((int(im.width * s), h), Image.LANCZOS)

def shadowed(base, im, xy, r=18, a=80):
    sh = Image.new('RGBA', base.size, (0, 0, 0, 0)); al = im.split()[3].point(lambda v: a if v > 10 else 0)
    sh.paste((40, 30, 60, 255), (xy[0], xy[1] + 14), al); base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r))); base.alpha_composite(im, xy)

def etext(d, im, xy, txt, font, fill=(30, 30, 40)):
    """text with leading emoji support: '{☕}text'"""
    x, y = xy
    while txt:
        if txt.startswith('{') and '}' in txt:
            e, txt = txt[1:txt.index('}')], txt[txt.index('}') + 1:]
            em = emoji(e, int(font.size * 1.05)); im.alpha_composite(em, (int(x), int(y + font.size * 0.12))); x += em.width + 6
        else:
            j = txt.find('{'); seg = txt if j < 0 else txt[:j]; txt = '' if j < 0 else txt[j:]
            d.text((x, y), seg, font=font, fill=fill); x += d.textlength(seg, font=font)

def fit_font(d, txt, path, size, maxw):
    while size > 16 and d.textlength(txt, font=F(path, size)) > maxw: size -= 2
    return F(path, size)

# ---------------- phone mocks (screen 560x1000) ----------------
def phone(mode, p):
    w, h = 560, 1000
    im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w + 39, h + 39), 70, fill=(25, 25, 32))
    dark = mode in ('reel', 'story')
    scr = Image.new('RGBA', (w, h), (18, 18, 22, 255) if dark else (255, 255, 255, 255)); s = ImageDraw.Draw(scr)
    globals()['_ph_' + mode](scr, s, w, h, p)
    s.rounded_rectangle((w // 2 - 70, 14, w // 2 + 70, 44), 15, fill=(25, 25, 32))
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 52, fill=255)
    im.paste(scr, (20, 20), m)
    return im

def _avatar(scr, s, x, y, r, e, col=(220, 200, 180), ring=True):
    if ring:
        g = grad(2 * r + 14, 2 * r + 14, IGG).convert('RGBA'); m = Image.new('L', g.size, 0); ImageDraw.Draw(m).ellipse((0, 0, g.width - 1, g.height - 1), fill=255)
        scr.paste(g, (x - r - 7, y - r - 7), m); s.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=(255, 255, 255))
    s.ellipse((x - r + 4, y - r + 4, x + r - 4, y + r - 4), fill=col)
    if e: em = emoji(e, int(r * 1.0)); scr.alpha_composite(em, (x - em.width // 2, y - em.height // 2))

def _ph_profile(scr, s, w, h, p):
    s.text((30, 70), p.get('user', 'my_account'), font=F(BLK, 30), fill=(20, 20, 20))
    _avatar(scr, s, 105, 205, 62, p.get('icon', '🙂'), tuple(p.get('icon_col', (220, 200, 180))), ring=p.get('ring', True))
    for i, (n, l) in enumerate(zip(p.get('stats', ['120', '1,000', '200']), ['投稿', 'フォロワー', 'フォロー'])):
        cx = 270 + i * 105; s.text((cx, 175), n, font=F(BLK, 34), fill=(20, 20, 20), anchor='mm'); s.text((cx, 222), l, font=F(BLD, 20), fill=(90, 90, 90), anchor='mm')
    y = 300; s.text((30, y), p.get('name', 'なまえ'), font=fit_font(s, p.get('name', ''), BLK, 30, w - 60), fill=(20, 20, 20)); y += 50
    if p.get('category'): s.text((30, y), p['category'], font=F(BLD, 24), fill=(120, 120, 120)); y += 40
    for line in p.get('bio', []):
        etext(s, scr, (30, y), line, F(BLD, 26)); y += 42
    if p.get('link'): s.text((30, y + 2), p['link'], font=F(BLD, 25), fill=(40, 90, 200)); y += 46
    s.rounded_rectangle((30, y + 10, 270, y + 66), 14, fill=(0, 149, 246)); s.text((150, y + 38), 'フォロー', font=F(BLK, 26), fill='white', anchor='mm')
    s.rounded_rectangle((285, y + 10, 525, y + 66), 14, fill=(239, 239, 239)); s.text((405, y + 38), 'メッセージ', font=F(BLK, 26), fill=(20, 20, 20), anchor='mm')
    y += 94
    hls = p.get('highlights', [])
    for i, (t, e) in enumerate(hls[:4]):
        cx = 75 + i * 120; on = p.get('hl_on') is None or p.get('hl_on') == i
        s.ellipse((cx - 44, y, cx + 44, y + 88), outline=(PINK if p.get('hl_on') == i else (200, 200, 200)), width=6 if p.get('hl_on') == i else 3, fill=(250, 245, 240))
        if e: em = emoji(e, 44); scr.alpha_composite(em, (cx - em.width // 2, y + 44 - em.height // 2))
        if t: s.text((cx, y + 110), t, font=F(BLD, 20), fill=(30, 30, 30), anchor='mm')
    if hls: y += 140
    cols = p.get('grid_cols') or [(214, 168, 120), (240, 220, 190), (160, 120, 90), (250, 200, 170), (200, 150, 110), (235, 210, 175), (220, 190, 160), (190, 150, 120), (245, 225, 200)]
    ems = p.get('grid', ['☕'] * 9); gw = (w - 8) // 3
    for i in range(9):
        x0 = (i % 3) * (gw + 4); y0 = y + (i // 3) * (gw + 4)
        if y0 > h: break
        s.rectangle((x0, y0, x0 + gw, y0 + gw), fill=tuple(cols[i % len(cols)]))
        if ems and ems[i % len(ems)]: em = emoji(ems[i % len(ems)], 70); scr.alpha_composite(em, (x0 + gw // 2 - em.width // 2, y0 + gw // 2 - em.height // 2))
        if p.get('grid_text'): s.text((x0 + gw // 2, y0 + gw - 26), p['grid_text'][i % len(p['grid_text'])], font=F(BLK, 22), fill='white', anchor='mm', stroke_width=3, stroke_fill=(60, 40, 30))

def _ph_post(scr, s, w, h, p):
    s.text((30, 70), 'Instagram' if False else '投稿', font=F(BLK, 30), fill=(20, 20, 20))
    _avatar(scr, s, 60, 150, 26, p.get('icon', '🙂'), ring=True); s.text((100, 150), p.get('user', 'my_account'), font=F(BLK, 26), fill=(20, 20, 20), anchor='lm')
    top = 200; sq = w
    scr.paste(grad(sq, sq, [tuple(c) for c in p.get('cols', [(250, 220, 200), (240, 190, 170)])]), (0, top))
    em = emoji(p.get('emoji', '☕'), 300); scr.alpha_composite(em, (w // 2 - em.width // 2, top + sq // 2 - em.height // 2))
    if p.get('overlay'): s.multiline_text((w // 2, top + 90), p['overlay'], font=F(BLK, 48), fill='white', anchor='mm', align='center', stroke_width=6, stroke_fill=(60, 40, 40))
    if p.get('dots'):
        for i in range(p['dots']): s.ellipse((w // 2 - p['dots'] * 9 + i * 18, top + sq + 16, w // 2 - p['dots'] * 9 + i * 18 + 10, top + sq + 26), fill=(0, 149, 246) if i == 0 else (200, 200, 200))
    y = top + sq + 40
    for i, e in enumerate(['♡', '💬', '➤']):
        if e == '♡': s.text((30 + i * 70, y), '♡', font=F(BLK, 44), fill=(20, 20, 20))
        else: em = emoji(e, 40); scr.alpha_composite(em, (30 + i * 70, y + 4))
    em = emoji('🔖', 40); scr.alpha_composite(em, (w - 70, y + 4))
    y += 70
    s.text((30, y), p.get('likes', 'いいね！ 1,234件'), font=F(BLK, 24), fill=(20, 20, 20)); y += 40
    for line in p.get('caption', []):
        etext(s, scr, (30, y), line, F(BLD, 23)); y += 36
    for tag in p.get('tags', []):
        s.text((30, y), tag, font=F(BLD, 23), fill=(40, 90, 200)); y += 34

def _ph_reel(scr, s, w, h, p):
    scr.paste(grad(w, h, [tuple(c) for c in p.get('cols', [(60, 40, 90), (220, 90, 120)])]), (0, 0))
    em = emoji(p.get('emoji', '💃'), 330); scr.alpha_composite(em, (w // 2 - em.width // 2, h // 2 - em.height // 2 - 40))
    if p.get('telop'): s.multiline_text((w // 2, 190), p['telop'], font=F(BLK, 50), fill=(255, 236, 90), anchor='mm', align='center', stroke_width=7, stroke_fill=(20, 20, 40))
    s.text((40, 70), 'リール', font=F(BLK, 32), fill='white')
    for i, (e, n) in enumerate([('♡', p.get('likes', '1.2万')), ('💬', '320'), ('➤', '')]):
        y = 560 + i * 120
        if e == '♡': s.text((w - 60, y), '♡', font=F(BLK, 54), fill='white', anchor='mm')
        else: em = emoji(e, 46); scr.alpha_composite(em, (w - 60 - em.width // 2, y - em.height // 2))
        if n: s.text((w - 60, y + 46), n, font=F(BLD, 20), fill='white', anchor='mm')
    _avatar(scr, s, 60, h - 170, 24, p.get('icon', '🙂'), ring=False); s.text((96, h - 170), p.get('user', 'my_account'), font=F(BLK, 24), fill='white', anchor='lm')
    s.text((40, h - 120), p.get('caption', ''), font=F(BLD, 22), fill='white')
    em = emoji('🎵', 26); scr.alpha_composite(em, (40, h - 76)); s.text((76, h - 64), p.get('sound', 'オリジナル音源'), font=F(BLD, 22), fill='white', anchor='lm')
    if p.get('progress') is not None:
        s.rectangle((0, h - 8, w, h), fill=(255, 255, 255, 80)); s.rectangle((0, h - 8, int(w * p['progress']), h), fill='white')

def _ph_story(scr, s, w, h, p):
    scr.paste(grad(w, h, [tuple(c) for c in p.get('cols', [(250, 200, 160), (240, 120, 150)])]), (0, 0))
    n = p.get('bars', 3)
    for i in range(n):
        x0 = 20 + i * (w - 40) // n; s.rounded_rectangle((x0, 60, x0 + (w - 40) // n - 8, 66), 3, fill='white' if i == 0 else (255, 255, 255, 120))
    _avatar(scr, s, 50, 110, 22, p.get('icon', '🙂'), ring=False); s.text((84, 110), p.get('user', 'my_account') + '  2時間', font=F(BLD, 22), fill='white', anchor='lm')
    em = emoji(p.get('emoji', '☕'), 240); scr.alpha_composite(em, (w // 2 - em.width // 2, 230))
    if p.get('text'): s.multiline_text((w // 2, 560), p['text'], font=F(BLK, 40), fill='white', anchor='mm', align='center', stroke_width=5, stroke_fill=(80, 40, 60))
    st = p.get('sticker')
    if st == 'question':
        s.rounded_rectangle((70, 640, w - 70, 820), 24, fill='white'); s.rounded_rectangle((70, 640, w - 70, 700), 24, fill=PINK); s.text((w // 2, 670), p.get('st_title', '質問してね！'), font=F(BLK, 28), fill='white', anchor='mm')
        s.text((w // 2, 760), 'ここに入力…', font=F(BLD, 26), fill=(150, 150, 150), anchor='mm')
    elif st == 'poll':
        s.rounded_rectangle((60, 640, w - 60, 860), 24, fill='white'); s.text((w // 2, 680), p.get('st_title', 'どっちが好き？'), font=F(BLK, 30), fill=(30, 30, 30), anchor='mm')
        for i, o in enumerate(p.get('options', ['A', 'B'])):
            s.rounded_rectangle((90, 720 + i * 66, w - 90, 776 + i * 66), 18, outline=(200, 200, 200), width=3); s.text((w // 2, 748 + i * 66), o, font=F(BLK, 28), fill=PURPLE, anchor='mm')
    elif st == 'link':
        s.rounded_rectangle((120, 680, w - 120, 760), 40, fill='white'); em = emoji('🔗', 36); scr.alpha_composite(em, (150, 702)); s.text((w // 2 + 20, 720), p.get('st_title', '予約はこちら'), font=F(BLK, 30), fill=BLUE, anchor='mm')
    elif st == 'mention':
        s.rounded_rectangle((120, 680, w - 120, 760), 16, fill='white'); s.text((w // 2, 720), p.get('st_title', '@friend'), font=F(BLK, 32), fill=ORANGE, anchor='mm')
    s.rounded_rectangle((30, h - 90, w - 110, h - 40), 25, outline='white', width=3); s.text((60, h - 65), 'メッセージを送信', font=F(BLD, 22), fill='white', anchor='lm')

def _ph_insight(scr, s, w, h, p):
    s.text((30, 70), p.get('title', 'インサイト'), font=F(BLK, 32), fill=(20, 20, 20)); s.text((30, 120), '過去30日間', font=F(BLD, 22), fill=(120, 120, 120))
    y = 180
    for lab, val, hi in p.get('rows', [('リーチしたアカウント', '12,340', False), ('保存数', '860', True), ('シェア数', '210', False)]):
        s.rounded_rectangle((24, y, w - 24, y + 96), 18, fill=(255, 240, 246) if hi else (246, 246, 248), outline=PINK if hi else None, width=4)
        s.text((48, y + 48), lab, font=F(BLD, 26), fill=(40, 40, 40), anchor='lm'); s.text((w - 48, y + 48), val, font=F(BLK, 34), fill=PINK if hi else (20, 20, 20), anchor='rm'); y += 112
    vals = p.get('bars', [3, 5, 4, 7, 6, 9, 12]); mx = max(vals); bw = (w - 100) // len(vals)
    base = h - 90
    for i, v in enumerate(vals):
        bh = int((base - y - 60) * v / mx); x0 = 50 + i * bw
        s.rounded_rectangle((x0 + 8, base - bh, x0 + bw - 8, base), 8, fill=PINK if i == len(vals) - 1 else (190, 170, 230))
    s.line((40, base, w - 40, base), fill=(200, 200, 200), width=3)

def _ph_dm(scr, s, w, h, p):
    _avatar(scr, s, 60, 100, 26, p.get('icon', '🙂'), ring=False); s.text((100, 100), p.get('user', 'お客さま'), font=F(BLK, 26), fill=(20, 20, 20), anchor='lm')
    s.line((0, 150, w, 150), fill=(230, 230, 230), width=2); y = 190
    for side, t in p.get('msgs', []):
        f = F(BLD, 25); lines = [t[i:i + 14] for i in range(0, len(t), 14)]; bh = 30 + 36 * len(lines); tw = max(s.textlength(l, font=f) for l in lines) + 40
        x0 = 30 if side == 'l' else w - 30 - tw
        s.rounded_rectangle((x0, y, x0 + tw, y + bh), 26, fill=(239, 239, 239) if side == 'l' else (120, 90, 240))
        for k, l in enumerate(lines): s.text((x0 + 20, y + 16 + k * 36), l, font=f, fill=(20, 20, 20) if side == 'l' else 'white')
        y += bh + 22
    s.rounded_rectangle((24, h - 90, w - 24, h - 36), 27, outline=(210, 210, 210), width=3); s.text((54, h - 63), 'メッセージ…', font=F(BLD, 22), fill=(150, 150, 150), anchor='lm')

def _ph_settings(scr, s, w, h, p):
    s.text((30, 70), p.get('title', '設定'), font=F(BLK, 34), fill=(20, 20, 20)); y = 150
    for i, row in enumerate(p.get('rows', [])):
        e, t = row[0], row[1]; hi = len(row) > 2 and row[2]
        if hi: s.rounded_rectangle((14, y - 6, w - 14, y + 82), 18, fill=(255, 236, 244), outline=PINK, width=4)
        em = emoji(e, 40); scr.alpha_composite(em, (40, y + 18)); s.text((100, y + 38), t, font=fit_font(s, t, BLD, 28, w - 170), fill=(20, 20, 20), anchor='lm')
        s.text((w - 40, y + 38), '›', font=F(BLK, 36), fill=(170, 170, 170), anchor='mm'); s.line((100, y + 84, w - 20, y + 84), fill=(236, 236, 236), width=2); y += 96

# ---------------- slide templates ----------------
def tag_pill(d, xy, text, col, size=38):
    f = F(BLK, size); tw = d.textlength(text, font=f); x, y = xy
    d.rounded_rectangle((x, y, x + tw + 60, y + size + 30), (size + 30) // 2, fill=col); d.text((x + 30 + tw / 2, y + (size + 30) / 2), text, font=f, fill='white', anchor='mm')

def mark(d, cx, cy, kind, r=110):
    if kind == 'ok': d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GREEN, width=32)
    elif kind == 'ng':
        d.line((cx - r, cy - r, cx + r, cy + r), fill=RED, width=34); d.line((cx + r, cy - r, cx - r, cy + r), fill=RED, width=34)

def make(spec, path, seed=0):
    t = spec['t']; im = pastel(seed); d = ImageDraw.Draw(im)
    if t == 'title':
        ph = phone(spec.get('mode', 'profile'), spec.get('p', {})).resize((408, 727), Image.LANCZOS); shadowed(im, ph, (PW - 470, 26))
    elif t == 'cards':
        items = spec['items']; n = len(items); hi = spec.get('hi')
        cols = 2 if n == 4 else n; rows = 2 if n == 4 else 1
        cw = (PW - 100 - (cols - 1) * 40) // cols; ch = 310 if rows == 2 else 560
        for i, it in enumerate(items):
            e, lab = it[0], it[1]; c = CARD_COLS[i % 6]
            x0 = 50 + (i % cols) * (cw + 40); y0 = (50 if rows == 2 else 110) + (i // cols) * (ch + 40)
            on = hi is None or hi == i
            card = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
            cd.rounded_rectangle((0, 0, cw - 1, ch - 1), 40, fill='white', outline=c, width=8 if hi == i else 4)
            if spec.get('num', True):
                cd.ellipse((26, 26, 126, 126), fill=c); cd.text((76, 78), str(i + 1), font=F(BLK, 64), fill='white', anchor='mm')
            if rows == 2:
                em = emoji(e, 110); card.alpha_composite(em, (cw - 36 - em.width, 30))
                cd.multiline_text((cw // 2, 222), lab, font=fit_font(cd, max(lab.split('\n'), key=len), BLK, 54, cw - 60), fill=(30, 30, 50), anchor='mm', align='center', spacing=8)
            else:
                em = emoji(e, min(180, cw - 80)); card.alpha_composite(em, (cw // 2 - em.width // 2, 150))
                cd.multiline_text((cw // 2, ch - 120), lab, font=fit_font(cd, max(lab.split('\n'), key=len), BLK, 46, cw - 40), fill=(30, 30, 50), anchor='mm', align='center', spacing=10)
            if not on: card.putalpha(card.split()[3].point(lambda v: int(v * 0.33)))
            if hi == i: card = card.resize((int(cw * 1.06), int(ch * 1.06)), Image.LANCZOS); x0 -= int(cw * 0.03); y0 -= int(ch * 0.03)
            shadowed(im, card, (x0, y0), a=60 if on else 0)
    elif t == 'phone':
        ph = phone(spec['mode'], spec.get('p', {})).resize((420, 750), Image.LANCZOS)
        side = spec.get('side')
        x = PW // 2 - 210 if not (side or spec.get('note')) else 120
        shadowed(im, ph, (x, 15))
        if spec.get('label'): tag_pill(d, (x + 20, 6), spec['label'], spec.get('label_col') and tuple(spec['label_col']) or PINK)
        if side: mark(d, 900, 390, side)
        if spec.get('note'):
            notes = spec['note'] if isinstance(spec['note'], list) else [spec['note']]
            for i, n in enumerate(notes):
                y = 390 - (len(notes) - 1) * 70 + i * 140
                d.rounded_rectangle((640, y - 52, PW - 50, y + 52), 52, fill=CARD_COLS[i % 6]); etext(d, im, (680, y - 28), n, F(BLK, 40), fill='white')
    elif t == 'compare':
        for k, (sp_, lab, col, mk) in enumerate([(spec['a'], spec.get('la', 'ビフォー'), (90, 90, 110), 'ng'), (spec['b'], spec.get('lb', 'アフター'), PINK, 'ok')]):
            ph = phone(sp_['mode'], sp_.get('p', {})).resize((400, 714), Image.LANCZOS); x = 110 if k == 0 else PW - 510
            shadowed(im, ph, (x, 40)); tag_pill(d, (x + 30, 8), lab, col)
        d.text((PW // 2, 400), '▶', font=F(BLK, 120), fill=PINK, anchor='mm')
    elif t == 'big':
        em = emoji(spec['e'], spec.get('size', 380)); im.alpha_composite(em, (PW // 2 - em.width // 2 + spec.get('dx', 0), PH // 2 - em.height // 2 - 20))
        for j, e2 in enumerate(spec.get('around', [])):
            a = j * 2 * math.pi / max(1, len(spec['around'])) - math.pi / 2; e3 = emoji(e2, 130)
            im.alpha_composite(e3, (int(PW // 2 + 420 * math.cos(a) - e3.width // 2), int(PH // 2 - 20 + 260 * math.sin(a) - e3.height // 2)))
        if spec.get('caption'): tag_pill(d, (PW // 2 - d.textlength(spec['caption'], font=F(BLK, 44)) // 2 - 30, PH - 110), spec['caption'], PINK, 44)
    elif t == 'photo':
        ph = Image.open(os.path.join(PHOTOS, spec['file'])).convert('RGB'); r = max(PW / ph.width, PH / ph.height)
        ph = ph.resize((int(ph.width * r) + 1, int(ph.height * r) + 1), Image.LANCZOS); im = ph.crop(((ph.width - PW) // 2, (ph.height - PH) // 2, (ph.width - PW) // 2 + PW, (ph.height - PH) // 2 + PH)).convert('RGBA')
    elif t == 'hw':
        d.rounded_rectangle((120, 60, 780, 740), 30, fill=(255, 255, 250)); d.rectangle((120, 60, 170, 740), fill=(240, 120, 150))
        for i in range(9): d.line((200, 160 + i * 64, 740, 160 + i * 64), fill=(200, 215, 235), width=3)
        for i, tx in enumerate(spec['items'][:5]):
            d.text((210, 100 + i * 120), '□', font=F(BLK, 46), fill=(120, 120, 140)); d.text((268, 102 + i * 120), tx, font=fit_font(d, tx, BLK, 42, 490), fill=(40, 40, 70))
        e = emoji('✏️', 200); im.alpha_composite(e.rotate(-15, expand=True), (660, 420))
        r = sprite('cheer', 500); im.alpha_composite(r, (PW - r.width - 50, PH - r.height - 40))
    elif t == 'next':
        d.rounded_rectangle((90, 180, 720, 600), 40, fill='white', outline=PINK, width=6)
        d.text((405, 250), '次回', font=F(BLK, 56), fill=PINK, anchor='mm')
        d.multiline_text((405, 430), spec['title'], font=fit_font(d, max(spec['title'].split('\n'), key=len), BLK, 70, 560), fill=(30, 30, 60), anchor='mm', align='center', spacing=14)
        g = grad(360, 360, IGG).convert('RGBA'); m = Image.new('L', (360, 360), 0); ImageDraw.Draw(m).ellipse((0, 0, 359, 359), fill=255)
        im.paste(g, (800, 210), m); d.ellipse((818, 228, 1142, 552), fill='white'); d.ellipse((832, 242, 1128, 538), fill=(250, 236, 220))
        r = sprite('smile', 260); im.alpha_composite(r, (980 - r.width // 2, 260))
    elif t == 'end':
        d.rounded_rectangle((140, 120, PW - 140, 620), 40, fill='white', outline=PINK, width=6)
        d.text((PW // 2, 240), 'インスタ講座', font=F(BLK, 60), fill=PINK, anchor='mm'); d.text((PW // 2, 380), '全20回 修了！', font=F(BLK, 100), fill=(30, 30, 60), anchor='mm')
        e = emoji('🎉', 140); im.alpha_composite(e, (200, 440)); im.alpha_composite(e.transpose(Image.FLIP_LEFT_RIGHT), (PW - 340, 440))
    im.convert('RGB').save(path, quality=92)

# ---------------- background + bgm ----------------
def classroom(path):
    W, H = 1920, 1080
    bg = Image.new('RGB', (W, H), (253, 243, 220)); d = ImageDraw.Draw(bg)
    for x in range(0, W, 60): d.rectangle((x, 0, x + 30, 900), fill=(250, 238, 212))
    d.rectangle((0, 0, W, 110), fill=(120, 84, 50)); d.rectangle((14, 0, W - 14, 96), fill=(46, 98, 72))
    rnd = random.Random(1)
    for i in range(60):
        x = rnd.randint(30, W - 30); y = rnd.randint(10, 85); d.line((x, y, x + rnd.randint(10, 60), y + rnd.randint(-4, 4)), fill=(70, 124, 96), width=2)
    d.rectangle((0, 96, W, 110), fill=(160, 116, 72))
    d.rounded_rectangle((1390, 180, 1840, 520), 12, fill='white'); d.rectangle((1404, 194, 1826, 506), fill=(150, 210, 245))
    d.ellipse((1450, 240, 1580, 300), fill='white'); d.ellipse((1540, 225, 1680, 295), fill='white')
    d.line((1615, 194, 1615, 506), fill='white', width=12); d.line((1404, 350, 1826, 350), fill='white', width=12)
    d.rectangle((0, 900, W, 940), fill=(196, 140, 86)); d.rectangle((0, 896, W, 904), fill=(150, 100, 60)); d.rectangle((0, 940, W, H), fill=(214, 160, 104))
    for i in range(-14, 30): x = W // 2 + i * 110; d.line((W // 2 + (x - W // 2) * 0.35, 940, x, H), fill=(190, 136, 84), width=4)
    d.line((0, 1000, W, 1000), fill=(198, 144, 90), width=3)
    d.rectangle((1820, 820, 1890, 900), fill=(200, 110, 70))
    for a in range(-60, 61, 30): d.ellipse((1855 + a - 40, 700 + abs(a), 1855 + a + 40, 830), fill=(80, 160, 90))
    bg.save(path)

def lofi(path):
    sr = 44100; beat = 60 / 82; bar = 4 * beat
    n2f = lambda n: 440 * 2 ** ((n - 69) / 12)
    prog = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]; bass = [41, 40, 38, 36]
    L = int(sr * bar * 4); out = np.zeros(L)
    def env(n, a, dcy): x = np.arange(n) / sr; return np.minimum(1, x / a) * np.exp(-x / dcy)
    def ep(f, dur, vel):
        n = int(dur * sr); x = np.arange(n) / sr
        s = np.sin(2 * np.pi * f * x) + 0.35 * np.sin(4 * np.pi * f * x) * np.exp(-x * 3) + 0.12 * np.sin(6 * np.pi * f * x) * np.exp(-x * 5)
        return vel * s * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * x)) * env(n, 0.006, 1.8)
    def put(seg, s0): out[s0:s0 + len(seg)] += seg[:max(0, L - s0)]
    for bi, ch in enumerate(prog):
        st = int(bi * bar * sr)
        for hit, (off, dur) in enumerate([(0, bar * 0.9), (beat * 2.5, beat * 1.4)]):
            for k, nn in enumerate(ch): put(ep(n2f(nn + 12), dur, 0.07 if hit else 0.09), st + int((off + k * 0.012) * sr))
        put(ep(n2f(bass[bi]), bar * 0.95, 0.22), st)
        for o, nn in zip([beat, beat * 1.5, beat * 3], [ch[3] + 12, ch[2] + 12, ch[3] + 14]): put(ep(n2f(nn), beat * 0.9, 0.05), st + int(o * sr))
    rng = np.random.default_rng(1)
    for i in range(16):
        s0 = int(i * beat * sr)
        if i % 2 == 0:
            n = int(0.25 * sr); x = np.arange(n) / sr; put(0.5 * np.sin(2 * np.pi * (55 + 90 * np.exp(-x * 30)) * x) * np.exp(-x * 12), s0)
        else:
            n = int(0.2 * sr); x = np.arange(n) / sr; put(0.12 * rng.standard_normal(n) * np.exp(-x * 18), s0)
        for hh in (0, 0.5):
            n = int(0.05 * sr); z = 0.035 * rng.standard_normal(n) * np.exp(-np.arange(n) / sr * 80); put(np.diff(np.concatenate([[0], z])), s0 + int(hh * beat * sr))
    out += 0.004 * rng.standard_normal(L); out = np.convolve(out, np.ones(6) / 6, mode='same'); out = np.tanh(out * 1.3) * 0.6
    st = np.stack([out, np.roll(out, int(0.012 * sr))], 1)
    w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
