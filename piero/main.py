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
    texts = [unit['hook_v']] + [thin(it['v']) for it in items] + [unit['end_v']]
    gaps = [0.3] + [0.22] * 9 + [0.45] + [0]
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
    t_img = E.text_img('\n'.join(title_split2(title)), E.font(165), RED, (120, 0, 0), stroke=12, spacing=0, max_w=1080)
    ov.append(dict(s=0, e=1e9, img=t_img, xy=(540, t_img.height // 2 - 40), jitter=2))   # title: top of the screen, biggest text
    YN = t_img.height - 40 - 60 + 62                 # just under the title (60 = text_img padding)
    sub_img = E.text_img('知らないとヤバい10選', f_t2, WHITE, (90, 0, 0), stroke=8, max_w=1000)
    ov.append(dict(s=0, e=segs[1][0], img=sub_img, xy=(540, YN)))           # intro only; the item number takes this spot later
    ov.append(dict(s=segs[-1][0], e=1e9, img=sub_img, xy=(540, YN)))
    YP = YN + 215; YC = (YP + 175 + 1170) // 2      # caption sits between the photo and the clown's head (face never covered)
    f_cap = E.font(96)
    photo_t = []
    for i, (s, e) in enumerate(segs):
        nxt = segs[i + 1][0] if i + 1 < len(segs) else total
        s0 = 0 if i == 0 else s
        if i == 0:
            cues.append(dict(s=s0, e=e, expr=1, mood='intro'))
            if thumb_pic is not None:
                ov.append(dict(s=0, e=nxt, img=I.evidence_card(thumb_pic, 540, 290, seed=11), xy=(540, YP), jitter=1))
            for ps, pe, p in assign_pages(s0, nxt, e, ['ククク……', f'{title}\n10選']):
                ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_cap, max_w=1040), xy=(540, YC), anim='pop', jitter=3))
        elif i <= 10:
            it = items[i - 1]
            last = i == 10
            cues.append(dict(s=s, e=e, expr=[0, 3, 5, 2, 8, 0, 3, 5, 2, 4][i - 1], mood='scare' if last else 'head'))
            ov.append(dict(s=s, e=nxt, img=E.text_img(f'その{i}', E.font(90), RED, (150, 0, 0), max_w=900), xy=(540, YN), anim='bigpop', jitter=2))
            if pics[i - 1] is not None:
                ov.append(dict(s=s, e=nxt, img=I.evidence_card(pics[i - 1], 540, 290, seed=i), xy=(540, YP), anim='pop', jitter=1))
                photo_t.append(s)
            ov.append(dict(s=s, e=nxt, img=E.text_img(it['t'], f_cap, max_w=1040), xy=(540, YC), anim='pop', jitter=3))
        else:
            cues.append(dict(s=s, e=e, expr=6, mood='outro'))
            for ps, pe, p in assign_pages(s, nxt, e, [pg for sent in split_sent(unit['end_v']) for pg in pages(sent, 9)]):
                ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_sub, max_w=1040), xy=(540, YC), anim='pop', jitter=3))
    heads = [s for (s, e), c in zip(segs, cues) if c['mood'] in ('head', 'scare')]
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track)
    A.sfx_for(total, heads, scares, w('sfx.wav'), photos=photo_t, heart=(segs[8][0], segs[10][1]))
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'))
    # the whole room (desk, candle, door, clown) sits lower so photo + caption fit above the face
    E.GEOM['short_low'] = dict(E.GEOM['short'], wain=1630, door=(30, 490, 1000, 1980), knob=(225, 1480), frame=(830, 1240),
                               table=1980, candle=(110, 1940), under=1320, nose=(540, 1600), SC=2.45)
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
    f_t, f_num, f_head, f_sub, f_big = E.font(64), E.font(120), E.font(100), E.font(70), E.font(120)
    PX = 1440   # right panel centre
    pics, thumb_pic = photos_for(unit)
    ov = [dict(s=0, e=1e9, img=E.text_img(f"{unit['title']} 10選", f_t, RED, (120, 0, 0), stroke=8, max_w=920), xy=(PX, 80), jitter=1)]
    cues = []
    n = len(segs)
    item_span = {}
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
        sub = texts[k]
        for ps, pe, p in assign_pages(s0, nxt, e, pages(sub, 21)):
            ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_sub, stroke=7, spacing=10, max_w=1820), xy=(960, 990), anim='pop', jitter=2))
    # right panel: intro title / item number + head / outro
    intro_end = segs[len(unit['intro'])][0]
    ov.append(dict(s=0, e=intro_end, img=E.text_img(f"{unit['title']}\n10選", f_big, RED, (150, 0, 0), max_w=900), xy=(PX, 300), anim='none', jitter=3))
    if thumb_pic is not None:
        ov.append(dict(s=0, e=intro_end, img=I.evidence_card(thumb_pic, 600, 340, seed=11), xy=(PX, 650), jitter=1))
    photo_t = []
    for ii, (s, e) in sorted(item_span.items()):
        p = pics[ii]
        ov.append(dict(s=s, e=e, img=E.text_img(f'その{ii + 1}', E.font(96), RED, (150, 0, 0), max_w=800), xy=(PX, 178 if p is not None else 300), anim='bigpop', jitter=2))
        if p is not None:
            ov.append(dict(s=s, e=e, img=E.text_img(unit['items'][ii]['head'], E.font(80), max_w=900), xy=(PX, 292), anim='pop', jitter=2))
            ov.append(dict(s=s, e=e, img=I.evidence_card(p, 700, 400, seed=ii), xy=(PX, 610), anim='pop', jitter=1))
            photo_t.append(s)
        else:
            hd = '\n'.join(wrap(unit['items'][ii]['head'], 7))
            ov.append(dict(s=s, e=e, img=E.text_img(hd, f_head, max_w=900), xy=(PX, 540), anim='pop', jitter=2))
    out_s = segs[-len(unit['outro'])][0]
    ov.append(dict(s=out_s, e=1e9, img=E.text_img('チャンネル登録\nしてくれよ……', f_head, max_w=900), xy=(PX, 470), anim='pop', jitter=3))
    heads = [s for (s, e), (kd, _) in zip(segs, kinds) if kd == 'head']
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track)
    A.sfx_for(total, heads, scares, w('sfx.wav'), photos=photo_t, heart=(item_span[9][0], item_span[9][1]) if 9 in item_span else None)
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'), bgm_vol=0.26)
    S = E.Scene('long', faces); T = E.Timeline(cues, env, ov, total, FPS_LONG)
    if thumb_out: make_thumb(faces, unit, thumb_out, thumb_pic, next((x for x in pics[::-1] if x is not None), None))
    if os.environ.get('PIERO_FRAMES'):
        for f in map(int, os.environ['PIERO_FRAMES'].split(',')): E.render_frame(S, T, f).save(f'{out}.{f}.jpg', quality=85)
        return None
    E.render_video(S, T, w('mix.wav'), out, tmp=w('tmp'))
    return out

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
        img.alpha_composite(card, (860, 660))
        d = ImageDraw.Draw(img)
        d.ellipse([930, 700, 1300, 990], outline=(240, 20, 20, 255), width=12)
    # text
    badge = Image.new('RGBA', (430, 120), (210, 0, 0, 255)); d = ImageDraw.Draw(badge)
    tw = d.textlength('閲覧注意', font=E.font(92)); d.text(((430 - tw) / 2, 4), '閲覧注意', font=E.font(92), fill=(255, 255, 255))
    badge = badge.rotate(4, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(badge, (60, 50))
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
    title = f"【閲覧注意】{u['title']}10選｜ピエロ君 #shorts"
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
        u = lst[st[key] % len(lst)]
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
