"""ピエロ君のやばい噂、知識 — daily auto post.
  python piero/main.py daily        render today's 3 videos and schedule them (12:00 short / 16:00 long / 20:00 short, JST)
  python piero/main.py test         render s001 + l001 (no upload) and attach them to a GitHub prerelease
  python piero/main.py test_short   only the short
  python piero/main.py one:<id>     render one unit (e.g. one:s005 / one:l003) to a prerelease"""
import os, sys, json, glob, re, datetime, subprocess, base64, hashlib, time, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import engine as E, audio as A, images as I
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
JST = datetime.timezone(datetime.timedelta(hours=9))
CHANNEL_NAME = 'ピエロ君のやばい噂、知識'
WORK = os.path.join(ROOT, '..', 'piero_work'); os.makedirs(WORK, exist_ok=True)
FPS_SHORT, FPS_LONG = 30, 24
RED, WHITE = (230, 25, 30), (245, 240, 230)

def jw(s): return sum(2 if unicodedata.east_asian_width(c) in 'FWA' else 1 for c in s) / 2

def wrap(text, n):
    """wrap Japanese text into lines of <= n full-width chars, preferring breaks after 、。…"""
    text = text.replace('\n', '')
    lines, cur = [], ''
    for ch in text:
        if jw(cur + ch) > n:
            k = max(cur.rfind('、'), cur.rfind('。'), cur.rfind('…'))
            if k >= len(cur) * 0.45 and k < len(cur) - 1:
                lines.append(cur[:k + 1]); cur = cur[k + 1:] + ch
            else:
                lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return [l.strip('、') or l for l in lines]

def pages(text, n, maxlines=2):
    ls = wrap(text, n)
    return ['\n'.join(ls[i:i + maxlines]) for i in range(0, len(ls), maxlines)]

def thin(v):
    """keep only one pause (the comma nearest the middle) so a short stays under 60 s"""
    parts = v.split('、')
    if len(parts) <= 2: return v
    k = min(range(1, len(parts)), key=lambda i: abs(len('、'.join(parts[:i])) - len(v) / 2))
    return ''.join(parts[:k]) + '、' + ''.join(parts[k:])

def split_sent(text):
    parts = re.split(r'(?<=[。！？])', text)
    return [p for p in (x.strip() for x in parts) if p]

def assign_pages(s, nxt_s, e, page_list):
    """spread pages over a cue by character count; returns [(start, end, text)]"""
    lens = [len(p.replace('\n', '')) + 2 for p in page_list]; tot = sum(lens); t = s; out = []
    for j, (p, ln) in enumerate(zip(page_list, lens)):
        d = (e - s) * ln / tot
        out.append((t, (t + d) if j < len(page_list) - 1 else nxt_s, p)); t += d
    return out

KW = None
def keywords(uid):
    global KW
    if KW is None:
        try: KW = json.load(open(os.path.join(ROOT, 'bank', 'keywords.json')))
        except Exception: KW = {}
    return KW.get(uid, [[]] * 10), KW.get(uid + '_thumb', [])

def photos_for(unit):
    """[(PIL image or None)] * 10, thumb image, credits"""
    qs, tq = keywords(unit['id'])
    used, credits, out = set(), [], []
    for i in range(10):
        im, cr = I.fetch(qs[i] if i < len(qs) else [], seed=i, used=used)
        out.append(im)
        if cr: credits.append(cr)
    th, cr = I.fetch(tq, seed=3, used=used)
    if cr: credits.append(cr)
    if th is None: th = next((x for x in out if x is not None), None)
    print('photos', unit['id'], sum(x is not None for x in out), '/ 10', 'thumb', th is not None)
    unit['_credits'] = credits
    return out, th

# ======================================================================== SHORT
def build_short(unit, out, faces, thumb_out=None):
    W, H = 1080, 1920
    items = unit['items']
    # opening: 1) the title is spoken first, 2) (new scripts) one scary line, 3) ククク hook — then the 10 items
    tv, tdisp = title_voice(unit)
    pre = [('title', tv, tdisp)] + ([('scare', unit['scare_v'], unit.get('scare_t') or unit['scare_v'])] if unit.get('scare_v') else [])
    hook = 'ククク……。' if unit.get('scare_v') else unit['hook_v'].replace('知らないとヤバい、', '')
    off = len(pre)
    texts = [p[1] for p in pre] + [hook] + [thin(it['v']) for it in items] + [unit['end_v']]
    gaps = [0.3] * off + [0.25] + [0.22] * 9 + [0.45] + [0]
    for speed in (1.05, 1.1, 1.16, 1.22, 1.3):
        v, segs, total = A.build_voice(texts, gaps, lead=0.5, tail=1.3, speed=speed)
        if total <= 58.5: break
    print('short', unit['id'], 'total', round(total, 1), 'speed', speed)
    w = lambda n: os.path.join(WORK, n)
    A.write(w('dry.wav'), v); A.voice_fx(w('dry.wav'), w('fx.wav'))
    nf = int(total * FPS_SHORT)
    env = A.envelope(v, FPS_SHORT, nf)
    cues, ov = [], []
    f_sub, f_num, f_t1, f_t2 = E.font(104), E.font(150), E.font(124), E.font(66)
    title = unit['title']
    pics, thumb_pic = photos_for(unit)
    if thumb_out: make_thumb_v(faces, unit, thumb_out, thumb_pic, next((x for x in pics[::-1] if x is not None), None))
    f_lab = E.font(34)
    # YouTube Shorts covers the top ~240px (status bar / search / menu) and the bottom ~380px (channel, title, share button):
    # everything important sits inside y 245..1540
    SAFE_TOP = 245
    t_img = E.text_img(title, E.font(150), RED, (120, 0, 0), stroke=11, max_w=900)   # one line; long titles shrink to fit
    ov.append(dict(s=0, e=1e9, img=t_img, xy=(540, SAFE_TOP - 60 + t_img.height // 2), jitter=2))   # title: biggest text, just under the app's top bar
    t_bot = SAFE_TOP + t_img.height - 120             # bottom of the title glyphs
    YP = t_bot + 185                                   # photo (card is ~300px tall incl. border)
    YN = YP - 112                                      # "その○" badge, drawn on top of the photo's top-left corner
    HEAD_TOP = 990
    YC = (YP + 140 + HEAD_TOP) // 2 + 5                    # caption between the photo and the clown's head
    f_cap = E.font(82)
    photo_t = []
    for j, (s, e) in enumerate(segs):
        nxt = segs[j + 1][0] if j + 1 < len(segs) else total
        i = j - off
        s0 = 0 if j == 0 else s
        if i < 0:   # opening lines: spoken title, then the scary line
            role, _, disp = pre[j]
            cues.append(dict(s=s0, e=e, expr=1 if role == 'title' else 2, mood='intro' if j == 0 else ''))
            if j == 0 and thumb_pic is not None:
                ov.append(dict(s=0, e=segs[off + 1][0], img=I.evidence_card(thumb_pic, 500, 265, seed=11), xy=(540, YP), jitter=1))
            if role == 'title':
                ov.append(dict(s=s0, e=nxt, img=E.text_img(disp, E.font(84), (255, 228, 40), (150, 0, 0), stroke=10, max_w=900), xy=(540, YC), jitter=2))
            else:
                ov.append(dict(s=s0, e=nxt, img=E.text_img(disp, E.font(88), RED, (150, 0, 0), stroke=10, max_w=900), xy=(540, YC), anim='pop', jitter=4))
        elif i == 0:
            cues.append(dict(s=s0, e=e, expr=1, mood=''))
            ov.append(dict(s=s0, e=nxt, img=E.text_img('ククク……', f_cap, max_w=900), xy=(540, YC), anim='pop', jitter=3))
        elif i <= 10:
            it = items[i - 1]
            last = i == 10
            cues.append(dict(s=s, e=e, expr=[0, 3, 5, 2, 8, 0, 3, 5, 2, 4][i - 1], mood='scare' if last else 'head'))
            if pics[i - 1] is not None:
                ov.append(dict(s=s, e=nxt, img=I.evidence_card(pics[i - 1], 500, 265, seed=i), xy=(540, YP), anim='pop', jitter=1))
                photo_t.append(s)
            ov.append(dict(s=s, e=nxt, img=E.text_img(f'その{i}', E.font(78), RED, (150, 0, 0), stroke=9, max_w=600), xy=(300, YN), anim='bigpop', jitter=2))
            ov.append(dict(s=s, e=nxt, img=E.text_img(it['t'], f_cap, max_w=900), xy=(540, YC), anim='pop', jitter=3))
        else:
            cues.append(dict(s=s, e=e, expr=6, mood='outro'))
            for ps, pe, p in assign_pages(s, nxt, e, [pg for sent in split_sent(unit['end_v']) for pg in pages(sent, 9)]):
                ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_cap, max_w=900), xy=(540, YC), anim='pop', jitter=3))
    heads = [s for (s, e), c in zip(segs, cues) if c['mood'] in ('head', 'scare')]
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track)
    A.sfx_for(total, heads, scares, w('sfx.wav'), photos=photo_t, heart=(segs[8 + off][0], segs[10 + off][1]))
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'))
    # the whole room (desk, candle, door, clown) sits lower so photo + caption fit above the face
    E.GEOM['short_low'] = dict(E.GEOM['short'], wain=1480, door=(30, 300, 820, 1845), knob=(225, 1300), frame=(820, 1060),
                               table=1845, candle=(150, 1805), under=1150, nose=(540, 1410), SC=2.5)
    ov.append(dict(s=0, e=1e9, img=I.horror_border(W, H, 80, seed=3), xy=(W // 2, H // 2)))   # old horror picture frame around the whole video (drawn last = on top)
    S = E.Scene('short_low', faces)
    T = E.Timeline(cues, env, ov, total, FPS_SHORT)
    if os.environ.get('PIERO_FRAMES'):
        for f in map(int, os.environ['PIERO_FRAMES'].split(',')): E.render_frame(S, T, f).save(f'{out}.{f}.jpg', quality=85)
        return None
    E.render_video(S, T, w('mix.wav'), out, tmp=w('tmp'))
    return out

# ======================================================================== LONG
def build_long(unit, out, faces, thumb_out=None):
    W, H = 1920, 1080
    texts, gaps, kinds = [], [], []   # kinds: (kind, item_index)
    texts.append(title_voice(unit)[0]); gaps.append(0.5); kinds.append(('intro', -1))     # the title is spoken first
    for sx in unit['intro']: texts.append(sx); gaps.append(0.4); kinds.append(('intro', -1))
    gaps[-1] = 0.8
    for i, it in enumerate(unit['items']):
        texts.append(f"その{'一二三四五六七八九十'[i]}。{it['head']}。"); gaps.append(0.55); kinds.append(('head', i))
        for sx in it['body']: texts.append(sx); gaps.append(0.35); kinds.append(('body', i))
        gaps[-1] = 0.9
    for sx in unit['outro']: texts.append(sx); gaps.append(0.45); kinds.append(('outro', -1))
    gaps[-1] = 0
    v, segs, total = A.build_voice(texts, gaps, lead=0.6, tail=2.5, speed=1.0)
    print('long', unit['id'], 'total', round(total, 1))
    w = lambda n: os.path.join(WORK, n)
    A.write(w('dry.wav'), v); A.voice_fx(w('dry.wav'), w('fx.wav'))
    nf = int(total * FPS_LONG)
    env = A.envelope(v, FPS_LONG, nf)
    # "every frame is a thumbnail" layout: huge hook words top-left, big clown on the right, evidence photo with a
    # red circle on his chest, red band with the current item, subtitles in the left column
    from PIL import ImageDraw
    pics, thumb_pic = photos_for(unit)
    l1, l2 = ((unit.get('thumb_text') or title_lines(unit['title'])) + [''])[:2]
    shade = np.zeros((H, W, 4), np.uint8)
    xx = np.arange(W, dtype=np.float32)[None, :].repeat(H, 0)
    shade[..., 3] = (np.clip(1.15 - xx / 1250, 0, 0.8) * 255).astype(np.uint8)        # darken the text side
    ov = [dict(s=0, e=1e9, img=Image.fromarray(shade, 'RGBA'), xy=(W // 2, H // 2))]
    badge = Image.new('RGBA', (360, 100), (210, 0, 0, 255)); db = ImageDraw.Draw(badge)
    tw = db.textlength('閲覧注意', font=E.font(78)); db.text(((360 - tw) / 2, 2), '閲覧注意', font=E.font(78), fill=(255, 255, 255))
    badge = badge.rotate(4, expand=True, resample=Image.BICUBIC)
    ov.append(dict(s=0, e=1e9, img=badge, xy=(60 + badge.width // 2, 40 + badge.height // 2)))
    t1 = E.text_img(l1, E.font(205), (255, 255, 255), (190, 0, 0), stroke=20, max_w=1150, grunge=False)
    ov.append(dict(s=0, e=1e9, img=t1, xy=(20 + t1.width // 2, 130 + t1.height // 2), jitter=1))
    if l2:
        t2 = E.text_img(l2, E.font(205), (255, 228, 40), (190, 0, 0), stroke=20, max_w=1150, grunge=False)
        ov.append(dict(s=0, e=1e9, img=t2, xy=(20 + t2.width // 2, 130 + t1.height - 95 + t2.height // 2), jitter=1))
    def band(text):
        f_b = E.font(74); tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=f_b)
        bw = int(min(1250, tw + 90)); im = Image.new('RGBA', (bw, 124), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (bw, 0), (bw - 30, 124), (0, 124)], fill=(200, 0, 0, 240))
        d.text((32, 18), text, font=f_b, fill=(255, 255, 255), stroke_width=4, stroke_fill=(60, 0, 0))
        return im
    def photo(pic, seed):
        card = I.evidence_card(pic, 440, 280, seed=seed)
        im = Image.new('RGBA', (card.width + 40, card.height + 40), (0, 0, 0, 0)); im.alpha_composite(card, (20, 20))
        ImageDraw.Draw(im).ellipse([90, 60, 460, 350], outline=(240, 20, 20, 255), width=12)
        return im
    PXY = (1500, 860); BY = H - 70 - 62                 # photo centre / band centre
    cues = []
    n = len(segs)
    item_span = {}
    f_sub = E.font(60)
    for k, ((s, e), (kind, ii)) in enumerate(zip(segs, kinds)):
        nxt = segs[k + 1][0] if k + 1 < n else total
        s0 = 0 if k == 0 else s
        if kind == 'head':
            item_span.setdefault(ii, [s, nxt])
        if kind in ('body',): item_span[ii][1] = nxt
        mood = {'intro': 'intro' if k == 0 else '', 'head': 'head', 'body': '', 'outro': 'outro' if kinds[k - 1][0] != 'outro' else ''}[kind]
        expr = {'intro': 1, 'head': 3, 'body': [0, 8, 5, 0, 2, 4, 8][k % 7], 'outro': 6}[kind]
        if kind == 'body' and ii == 9 and k + 1 < n and kinds[k + 1][0] == 'outro': mood = 'scare'
        cues.append(dict(s=s0, e=e, expr=expr, mood=mood))
        for ps, pe, pg in assign_pages(s0, nxt, e, pages(texts[k], 17)):
            ov.append(dict(s=ps, e=pe, img=E.text_img(pg, f_sub, stroke=7, spacing=8, max_w=1180), xy=(600, 760), anim='pop', jitter=1))
    intro_end = segs[len(unit['intro']) + 1][0]
    out_s = segs[-len(unit['outro'])][0]
    bi = band(f"{unit['title']}10選")
    ov.append(dict(s=0, e=intro_end, img=bi, xy=(bi.width // 2, BY)))
    if thumb_pic is not None:
        ov.append(dict(s=0, e=intro_end, img=photo(thumb_pic, 11), xy=PXY, jitter=1))
    photo_t = []
    for ii, (s, e) in sorted(item_span.items()):
        b = band(f"その{ii + 1}　{unit['items'][ii]['head']}")
        ov.append(dict(s=s, e=e, img=b, xy=(b.width // 2, BY), anim='bigpop'))
        if pics[ii] is not None:
            ov.append(dict(s=s, e=e, img=photo(pics[ii], ii), xy=PXY, anim='pop', jitter=1))
            photo_t.append(s)
    bo = band('チャンネル登録してくれよ……')
    ov.append(dict(s=out_s, e=1e9, img=bo, xy=(bo.width // 2, BY), anim='pop'))
    heads = [s for (s, e), (kd, _) in zip(segs, kinds) if kd == 'head']
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track)
    A.sfx_for(total, heads, scares, w('sfx.wav'), photos=photo_t, heart=(item_span[9][0], item_span[9][1]) if 9 in item_span else None)
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'), bgm_vol=0.26)
    E.GEOM['long_thumb'] = dict(E.GEOM['long'], wain=700, door=(1720, 180, 1900, 1080), knob=(1745, 620), table=1075, candle=(1110, 1040),
                                bulb=(1020, 30), L1c=((1440, 260), 760), vig=(0.72, 0.5, 0.75, 0.9), nose=(1440, 560), SC=2.8, under=640)
    S = E.Scene('long_thumb', faces); T = E.Timeline(cues, env, ov, total, FPS_LONG)
    if thumb_out: make_thumb(faces, unit, thumb_out, thumb_pic, next((x for x in pics[::-1] if x is not None), None))
    if os.environ.get('PIERO_FRAMES'):
        for f in map(int, os.environ['PIERO_FRAMES'].split(',')): E.render_frame(S, T, f).save(f'{out}.{f}.jpg', quality=85)
        return None
    E.render_video(S, T, w('mix.wav'), out, tmp=w('tmp'))
    return out

def title_voice(u):
    """(spoken title, on-screen title) from the YouTube title, e.g. 「乗る前に知りたくなかった、飛行機の裏知識、十選。」"""
    t = u.get('yt_title') or f"{u['title']}10選"
    t = re.sub(r'【[^】]*】', '', t).replace('#shorts', '').replace('｜ピエロ君', '').strip()
    head, _, rest = t.partition('…')
    if not rest: head, rest = '', head
    rest = rest.replace('10選', '').strip()
    spoken = (head + '、' if head else '') + rest + '、十選。'
    disp = (head + '\n' if head else '') + rest + '10選'
    return spoken, disp

def title_split2(t):
    """big short title: up to 5 chars one line; else two lines split after の/と (else after an い-adjective, else a katakana edge), never leaving 1 char alone"""
    if len(t) <= 5: return [t]
    ok = lambda i: 2 <= i <= len(t) - 2
    cands = [i for i in range(2, len(t) - 1) if t[i - 1] in 'のと' and ok(i)]
    if not cands: cands = [i for i in range(2, len(t) - 1) if t[i - 1] == 'い' and t[i] != 'い' and ok(i)]
    if not cands:
        kata = lambda c: '゠' <= c <= 'ヿ'
        cands = [i for i in range(2, len(t) - 1) if kata(t[i]) != kata(t[i - 1]) and ok(i)]
    if not cands: return [t]
    k = min(cands, key=lambda i: abs(i - len(t) / 2))
    return [t[:k], t[k:]]

def title_lines(t):
    """split a title into 1-2 lines at a natural point (after の/と/は/が) near the middle"""
    if len(t) <= 5: return [t]
    best = None
    for i in range(2, len(t) - 1):
        kata = lambda c: '゠' <= c <= 'ヿ'
        if t[i - 1] in 'のとはがなに' or (kata(t[i]) and not kata(t[i - 1])):
            sc = abs(i - len(t) / 2)
            if best is None or sc < best[0]: best = (sc, i)
    k = best[1] if best and best[0] <= 2.5 else (len(t) + 1) // 2
    return [t[:k], t[k:]]

def make_thumb(faces, unit, path, bg_pic=None, item_pic=None):
    """1280x720 thumbnail: dark photo background, huge laughing clown with red rim light, bold title"""
    from PIL import ImageFilter, ImageDraw
    W, H = 1920, 1080
    if bg_pic is not None:
        img = I.background(bg_pic, W, H, seed=5).convert('RGBA')
    else:
        img = Image.new('RGBA', (W, H), (25, 12, 10, 255))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # darken the text side, red glow behind the clown
    shade = np.clip(1.1 - xx / W * 1.1, 0, 0.85)[..., None]
    glow = np.exp(-(((xx - 1450) / 520) ** 2 + ((yy - 520) / 460) ** 2))[..., None]
    a = np.asarray(img).astype(np.float32)
    a[..., :3] = a[..., :3] * (1 - shade) + np.array([150, 0, 0]) * glow * 0.55
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # clown (laughing face) with red rim light
    f = (np.clip(faces[6], 0, 1) * 255).astype(np.uint8)
    cl = Image.fromarray(f).crop((20, 0, 440, 400))
    sc = 2.75; cl = cl.resize((int(cl.width * sc), int(cl.height * sc)), Image.LANCZOS).rotate(-4, expand=True, resample=Image.BICUBIC)
    ca = np.asarray(cl).astype(np.float32); ca[..., :3] *= np.array([1.05, 0.9, 0.82]); cl = Image.fromarray(np.clip(ca, 0, 255).astype(np.uint8))
    rim = Image.new('RGBA', cl.size, (255, 20, 20, 0)); rim.putalpha(cl.split()[3].filter(ImageFilter.GaussianBlur(26)).point(lambda v: min(255, v * 2)))
    cx, cy = 1460, 600
    img.alpha_composite(rim, (int(cx - cl.width / 2), int(cy - cl.height / 2)))
    img.alpha_composite(cl, (int(cx - cl.width / 2), int(cy - cl.height / 2)))
    # small evidence photo with red circle
    if item_pic is not None:
        card = I.evidence_card(item_pic, 440, 280, seed=2)
        cx0, cy0 = (1260, 720) if unit.get('thumb_text') else (860, 660)
        img.alpha_composite(card, (cx0, cy0))
        d = ImageDraw.Draw(img)
        d.ellipse([cx0 + 70, cy0 + 40, cx0 + 440, cy0 + 330], outline=(240, 20, 20, 255), width=12)
    # text
    badge = Image.new('RGBA', (430, 120), (210, 0, 0, 255)); d = ImageDraw.Draw(badge)
    tw = d.textlength('閲覧注意', font=E.font(92)); d.text(((430 - tw) / 2, 4), '閲覧注意', font=E.font(92), fill=(255, 255, 255))
    badge = badge.rotate(4, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(badge, (60, 50))
    if unit.get('thumb_text'):
        # the hook words, as big as possible: white line + yellow line, thick black edge and red glow
        l1, l2 = (unit['thumb_text'] + [''])[:2]
        t1 = E.text_img(l1, E.font(245), (255, 255, 255), (190, 0, 0), stroke=22, max_w=1060, grunge=False)
        t2 = E.text_img(l2, E.font(245), (255, 228, 40), (190, 0, 0), stroke=22, max_w=1060, grunge=False) if l2 else None
        img.alpha_composite(t1, (10, 170))
        if t2: img.alpha_composite(t2, (10, 170 + t1.height - 105))
        # topic band at the bottom-left
        band_t = f"{unit['title']}10選"
        f_b = E.font(84); d = ImageDraw.Draw(img); tw = d.textlength(band_t, font=f_b)
        bw = int(min(1180, tw + 90))
        band = Image.new('RGBA', (bw, 140), (0, 0, 0, 0)); db = ImageDraw.Draw(band)
        db.polygon([(0, 0), (bw, 0), (bw - 30, 140), (0, 140)], fill=(200, 0, 0, 240))
        db.text((34, 22), band_t, font=f_b, fill=(255, 255, 255), stroke_width=4, stroke_fill=(60, 0, 0))
        img.alpha_composite(band, (0, H - 190))
    else:
        lines = title_lines(unit['title'])
        t1 = E.text_img('\n'.join(lines), E.font(200 if len(lines) <= 2 else 160), (255, 255, 255), (200, 0, 0), stroke=18, spacing=6, max_w=1000, grunge=False)
        t2 = E.text_img('10選', E.font(300), (255, 226, 60), (200, 40, 0), stroke=20, max_w=760, grunge=False)
        img.alpha_composite(t1, (40, 210))
        img.alpha_composite(t2, (60, H - t2.height + 10))
    img.convert('RGB').resize((1280, 720), Image.LANCZOS).save(path, quality=93)

def make_thumb_v(faces, unit, path, bg_pic=None, item_pic=None):
    """1080x1920 vertical thumbnail for Shorts: badge, huge title, 10選, evidence photo, laughing clown at the bottom"""
    from PIL import ImageFilter, ImageDraw
    W, H = 1080, 1920
    img = I.background(bg_pic, W, H, seed=5).convert('RGBA') if bg_pic is not None else Image.new('RGBA', (W, H), (25, 12, 10, 255))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shade = np.clip(0.75 - yy / H * 0.5, 0.2, 0.75)[..., None]
    glow = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - 1500) / 460) ** 2))[..., None]
    a = np.asarray(img).astype(np.float32)
    a[..., :3] = a[..., :3] * (1 - shade) + np.array([160, 0, 0]) * glow * 0.6
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    f = (np.clip(faces[6], 0, 1) * 255).astype(np.uint8)
    cl = Image.fromarray(f).crop((20, 0, 440, 400))
    sc = 2.3; cl = cl.resize((int(cl.width * sc), int(cl.height * sc)), Image.LANCZOS).rotate(-4, expand=True, resample=Image.BICUBIC)
    ca = np.asarray(cl).astype(np.float32); ca[..., :3] *= np.array([1.05, 0.9, 0.82]); cl = Image.fromarray(np.clip(ca, 0, 255).astype(np.uint8))
    rim = Image.new('RGBA', cl.size, (255, 20, 20, 0)); rim.putalpha(cl.split()[3].filter(ImageFilter.GaussianBlur(26)).point(lambda v: min(255, v * 2)))
    pos = (int(W / 2 - cl.width / 2), H - cl.height + 40)
    img.alpha_composite(rim, pos); img.alpha_composite(cl, pos)
    badge = Image.new('RGBA', (430, 120), (210, 0, 0, 255)); d = ImageDraw.Draw(badge)
    tw = d.textlength('閲覧注意', font=E.font(92)); d.text(((430 - tw) / 2, 4), '閲覧注意', font=E.font(92), fill=(255, 255, 255))
    badge = badge.rotate(4, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(badge, (int(W / 2 - badge.width / 2), 60))
    lines = title_lines(unit['title'])
    t1 = E.text_img('\n'.join(lines), E.font(190 if len(lines) <= 2 else 150), (255, 255, 255), (200, 0, 0), stroke=18, spacing=6, max_w=1000, grunge=False)
    img.alpha_composite(t1, (int(W / 2 - t1.width / 2), 220))
    t2 = E.text_img('10選', E.font(260), (255, 226, 60), (200, 40, 0), stroke=20, max_w=700, grunge=False)
    img.alpha_composite(t2, (int(W / 2 - t2.width / 2), 230 + t1.height - 20))
    img.convert('RGB').save(path, quality=92)

# ======================================================================== YouTube
def yt_client():
    from cryptography.fernet import Fernet
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    sec = os.environ['YT_CLIENT_SECRET']
    rt = Fernet(base64.urlsafe_b64encode(hashlib.sha256(sec.encode()).digest())).decrypt(open(os.path.join(ROOT, 'rt.enc'), 'rb').read()).decode()
    cr = Credentials(None, refresh_token=rt, token_uri='https://oauth2.googleapis.com/token', client_id=os.environ['YT_CLIENT_ID'],
                     client_secret=sec, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly'])
    yt = build('youtube', 'v3', credentials=cr)
    ch = yt.channels().list(part='snippet', mine=True).execute().get('items', [])
    names = [c['snippet']['title'] for c in ch]
    if not any('ピエロ' in n for n in names): raise SystemExit(f'wrong channel: {names}')   # never post to another channel
    return yt

DESC_TAIL = ('\n\n暗い部屋から、ピエロが囁く。知らないとヤバい噂・裏技・裏知識を毎日お届け。\n'
             '毎日12時・20時にショート、16時に10選の解説動画を更新中。\n'
             '※噂・都市伝説は「そう言われている」話として紹介しています。\n\n'
             '#ピエロ #雑学 #闇 #都市伝説 #10選\n\n音声：Open JTalk\n制作：株式会社RPGエンターテイメント')

def upload(yt, path, title, desc, tags, publish_at=None, thumb=None):
    from googleapiclient.http import MediaFileUpload
    status = {'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False}
    if publish_at: status.update(privacyStatus='private', publishAt=publish_at)
    else: status.update(privacyStatus='public')
    body = {'snippet': {'title': title[:100], 'description': desc[:4900], 'tags': tags[:15], 'categoryId': '24',
                        'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True, chunksize=8 << 20))
    resp = None
    while resp is None:
        for k in range(6):   # the big long video sometimes gets its connection dropped mid-upload: resume instead of failing
            try: _, resp = req.next_chunk(num_retries=5); break
            except (OSError, ConnectionError) as e:
                print('upload chunk retry', k, repr(e)[:120]); time.sleep(15 * (k + 1))
        else: raise RuntimeError('upload failed after retries')
    vid = resp['id']; print('uploaded', vid, title, publish_at)
    if thumb:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype='image/jpeg')).execute(); print('thumb ok')
        except Exception as e: print('thumb failed (channel may need phone verification):', repr(e)[:300])
    return vid

def credits(u):
    c = u.get('_credits') or []
    return ('\n\n画像クレジット:\n' + '\n'.join(c)) if c else ''

def meta_short(u):
    title = u.get('yt_title') or f"【閲覧注意】{u['title']}10選｜ピエロ君 #shorts"
    lines = '\n'.join(f"{i + 1}. {it['t'].replace(chr(10), ' ')}" for i, it in enumerate(u['items']))
    return title, f"{u['title']} 10選\n\n{lines}" + DESC_TAIL + credits(u), u.get('tags', []) + ['ピエロ', '雑学', '闇', '都市伝説', '10選', 'shorts']

def meta_long(u):
    lines = '\n'.join(f"{i + 1}. {it['head']}" for i, it in enumerate(u['items']))
    return u['yt_title'], f"{u['title']} 10選\n\n{lines}" + DESC_TAIL + credits(u), u.get('tags', []) + ['ピエロ', '雑学', '闇', '都市伝説', '10選', '解説']

# ======================================================================== state / tasks
ST = os.path.join(ROOT, 'state', 'state.json')
def load_state():
    return json.load(open(ST)) if os.path.exists(ST) else {'next_short': 0, 'next_long': 0, 'days': {}}
def save_state(st):
    os.makedirs(os.path.dirname(ST), exist_ok=True); json.dump(st, open(ST, 'w'), ensure_ascii=False, indent=1)
    subprocess.run('git add piero/state && git commit -qm "piero: state [skip ci]" && '
                   'for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; sleep 5; done', shell=True)

def units(kind):
    """all scripts of a kind ('s' short / 'l' long), sorted by id. bank/<kind>_*.json each hold a list."""
    us = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'bank', f'{kind}_*.json'))): us += json.load(open(f))
    return sorted(us, key=lambda u: u['id'])

def unit(uid): return next(u for u in units(uid[0]) if u['id'] == uid)

def faces(): return E.load_faces(E.find_sheet(os.path.join(ROOT, 'assets')))

def release(tag, files, notes):
    subprocess.run(['gh', 'release', 'delete', tag, '-y', '--cleanup-tag'], capture_output=True)
    subprocess.run(['gh', 'release', 'create', tag, *files, '--title', tag, '--notes', notes, '--prerelease'], check=True)

def task_daily():
    now = datetime.datetime.now(JST); day = now.strftime('%Y%m%d')
    st = load_state(); dd = st['days'].setdefault(day, {})
    yt = yt_client(); F = faces(); thumbs = []
    shorts, longs = units('s'), units('l')
    for slot, kind, hh in (('A', 's', 12), ('L', 'l', 16), ('B', 's', 20)):
        if dd.get(slot, {}).get('video'): print('done', slot, dd[slot]); continue
        lst = shorts if kind == 's' else longs
        key = 'next_short' if kind == 's' else 'next_long'
        posted = {v['id'] for d in st['days'].values() for v in d.values() if v.get('id')}
        fresh = [x for x in lst if x['id'] not in posted]
        if not fresh:   # never re-upload an old script (duplicate videos hurt the channel) — wait for new scripts instead
            print('no new script left for', kind); continue
        u = fresh[0]
        when = now.replace(hour=hh, minute=0, second=0, microsecond=0)
        out = os.path.join(WORK, f'{day}_{slot}_{u["id"]}.mp4')
        if kind == 's':
            thumb = out[:-4] + '.jpg'; build_short(u, out, F, thumb); t, d, tags = meta_short(u)
        else:
            thumb = out[:-4] + '.jpg'; build_long(u, out, F, thumb); t, d, tags = meta_long(u)
        # schedule for the slot; if the slot is already (almost) past (late retry), publish right away
        late = when - datetime.datetime.now(JST) < datetime.timedelta(minutes=20)
        pub = None if late else when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        vid = upload(yt, out, t, d, tags, pub, thumb)
        dd[slot] = {'id': u['id'], 'video': vid, 'at': f'{hh}:00'}
        st[key] = st[key] + 1
        save_state(st)
        os.remove(out)
        if thumb and os.path.exists(thumb): thumbs.append(thumb)
    if thumbs:
        try: release(f'piero-thumbs-{day}', thumbs, 'thumbnails ' + day)
        except Exception as e: print('thumb release failed', repr(e)[:200])

def task_thumbs(ids, tag):
    """thumbnails only (no voice / video). ids like s001,l001,s002 or 'today' (= today's posted units)"""
    F = faces(); outs = []
    if ids == ['today']:
        day = datetime.datetime.now(JST).strftime('%Y%m%d'); dd = load_state()['days'].get(day, {})
        ids = [dd[k]['id'] for k in ('A', 'L', 'B') if k in dd]
    for n, i in enumerate(ids):
        u = unit(i); pics, th = photos_for(u)
        item = next((x for x in pics[::-1] if x is not None), None)
        p = os.path.join(WORK, f'thumb_{n + 1}_{i}.jpg')
        (make_thumb_v if i.startswith('s') else make_thumb)(F, u, p, th, item); outs.append(p)
    release(tag, outs, ' '.join(ids))

def task_render(ids, tag):
    F = faces(); outs = []
    for i in ids:
        out = os.path.join(WORK, f'test_{i}.mp4')
        if i.startswith('s'): build_short(unit(i), out, F)
        else:
            th = out[:-4] + '.jpg'; build_long(unit(i), out, F, th); outs.append(th)
        outs.append(out)
    release(tag, outs, ' '.join(ids))

if __name__ == '__main__':
    t0 = time.time()
    task = sys.argv[1] if len(sys.argv) > 1 else 'test'
    stamp = datetime.datetime.now(JST).strftime('%m%d%H%M')
    if task == 'daily': task_daily()
    elif task == 'test': task_render(['s001', 'l001'], f'piero-test-{stamp}')
    elif task == 'test_short': task_render(['s001'], f'piero-test-{stamp}')
    elif task.startswith('one:'): task_render([task[4:]], f'piero-{task[4:]}-{stamp}')
    elif task.startswith('thumbs:'): task_thumbs(task[7:].split(','), f'piero-thumbs-{stamp}')
    elif task == 'whoami': yt_client(); print('channel ok')
    print('elapsed', round(time.time() - t0), 's')
