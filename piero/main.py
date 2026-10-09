"""ピエロ君のやばい噂、知識 — daily auto post.
  python piero/main.py daily        render today's 3 videos and schedule them (12:00 short / 16:00 long / 20:00 short, JST)
  python piero/main.py test         render s001 + l001 (no upload) and attach them to a GitHub prerelease
  python piero/main.py test_short   only the short
  python piero/main.py one:<id>     render one unit (e.g. one:s005 / one:l003) to a prerelease"""
import os, sys, json, glob, re, datetime, subprocess, base64, hashlib, time, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import engine as E, audio as A

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

# ======================================================================== SHORT
def build_short(unit, out, faces):
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
    ov.append(dict(s=0, e=1e9, img=E.text_img(title, f_t1, RED, (120, 0, 0), max_w=1040), xy=(540, 140), jitter=2))
    ov.append(dict(s=0, e=1e9, img=E.text_img('知らないとヤバい10選', f_t2, WHITE, (90, 0, 0), stroke=8, max_w=1000), xy=(540, 272)))
    YC = 640
    for i, (s, e) in enumerate(segs):
        nxt = segs[i + 1][0] if i + 1 < len(segs) else total
        s0 = 0 if i == 0 else s
        if i == 0:
            cues.append(dict(s=s0, e=e, expr=1, mood='intro'))
            for ps, pe, p in assign_pages(s0, nxt, e, ['ククク……', f'{title}\n10選']):
                ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_sub, max_w=1040), xy=(540, YC), anim='pop', jitter=3))
        elif i <= 10:
            it = items[i - 1]
            last = i == 10
            cues.append(dict(s=s, e=e, expr=[0, 3, 5, 2, 8, 0, 3, 5, 2, 4][i - 1], mood='scare' if last else 'head'))
            ov.append(dict(s=s, e=nxt, img=E.text_img(f'その{i}', f_num, RED, (150, 0, 0), max_w=900), xy=(540, YC - 190), anim='bigpop', jitter=2))
            ov.append(dict(s=s, e=nxt, img=E.text_img(it['t'], f_sub, max_w=1040), xy=(540, YC + 40), anim='pop', jitter=3))
        else:
            cues.append(dict(s=s, e=e, expr=6, mood='outro'))
            for ps, pe, p in assign_pages(s, nxt, e, [pg for sent in split_sent(unit['end_v']) for pg in pages(sent, 9)]):
                ov.append(dict(s=ps, e=pe, img=E.text_img(p, f_sub, max_w=1040), xy=(540, YC), anim='pop', jitter=3))
    heads = [s for (s, e), c in zip(segs, cues) if c['mood'] == 'head']
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track); A.sfx_for(total, heads, scares, w('sfx.wav'))
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'))
    S = E.Scene('short', faces); T = E.Timeline(cues, env, ov, total, FPS_SHORT)
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
    ov.append(dict(s=0, e=intro_end, img=E.text_img(f"{unit['title']}\n10選", f_big, RED, (150, 0, 0), max_w=900), xy=(PX, 440), anim='none', jitter=3))
    for ii, (s, e) in sorted(item_span.items()):
        ov.append(dict(s=s, e=e, img=E.text_img(f'その{ii + 1}', f_num, RED, (150, 0, 0), max_w=800), xy=(PX, 300), anim='bigpop', jitter=2))
        hd = '\n'.join(wrap(unit['items'][ii]['head'], 7))
        ov.append(dict(s=s, e=e, img=E.text_img(hd, f_head, max_w=900), xy=(PX, 540), anim='pop', jitter=2))
    out_s = segs[-len(unit['outro'])][0]
    ov.append(dict(s=out_s, e=1e9, img=E.text_img('チャンネル登録\nしてくれよ……', f_head, max_w=900), xy=(PX, 470), anim='pop', jitter=3))
    heads = [s for (s, e), (kd, _) in zip(segs, kinds) if kd == 'head']
    scares = [e for (s, e), c in zip(segs, cues) if c['mood'] == 'scare']
    track = A.musicbox(w('musicbox.wav'))
    A.bgm_for(total, w('bgm.wav'), track); A.sfx_for(total, heads, scares, w('sfx.wav'))
    A.mix(w('fx.wav'), w('bgm.wav'), w('sfx.wav'), w('mix.wav'), bgm_vol=0.26)
    S = E.Scene('long', faces); T = E.Timeline(cues, env, ov, total, FPS_LONG)
    if thumb_out: make_thumb(S, unit, thumb_out)
    if os.environ.get('PIERO_FRAMES'):
        for f in map(int, os.environ['PIERO_FRAMES'].split(',')): E.render_frame(S, T, f).save(f'{out}.{f}.jpg', quality=85)
        return None
    E.render_video(S, T, w('mix.wav'), out, tmp=w('tmp'))
    return out

def make_thumb(S, unit, path):
    T = E.Timeline([dict(s=0, e=1, expr=6, mood='')], np.zeros(10), [], 1, 24)
    g0 = S.g; S.g = dict(g0, SC=2.5, nose=(560, 620))
    img = E.render_frame(S, T, 0).convert('RGBA'); S.g = g0
    t1 = E.text_img('\n'.join(wrap(unit['title'], 6)), E.font(190), RED, (160, 0, 0), stroke=14, max_w=1060)
    t2 = E.text_img('10選', E.font(230), (255, 236, 120), (150, 60, 0), stroke=14, max_w=700)
    tag = E.text_img('知らないとヤバい', E.font(88), WHITE, (100, 0, 0), stroke=9, max_w=900)
    img.alpha_composite(tag, (1430 - tag.width // 2, 110 - tag.height // 2))
    img.alpha_composite(t1, (1430 - t1.width // 2, 470 - t1.height // 2))
    img.alpha_composite(t2, (1430 - t2.width // 2, 860 - t2.height // 2))
    img.convert('RGB').resize((1280, 720), E.Image.LANCZOS).save(path, quality=92)

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
    status = {'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': True}
    if publish_at: status.update(privacyStatus='private', publishAt=publish_at)
    else: status.update(privacyStatus='public')
    body = {'snippet': {'title': title[:100], 'description': desc[:4900], 'tags': tags[:15], 'categoryId': '24',
                        'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True, chunksize=8 << 20))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    vid = resp['id']; print('uploaded', vid, title, publish_at)
    if thumb:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype='image/jpeg')).execute(); print('thumb ok')
        except Exception as e: print('thumb failed (channel may need phone verification):', repr(e)[:300])
    return vid

def meta_short(u):
    title = f"【閲覧注意】{u['title']}10選｜ピエロ君 #shorts"
    lines = '\n'.join(f"{i + 1}. {it['t'].replace(chr(10), ' ')}" for i, it in enumerate(u['items']))
    return title, f"{u['title']} 10選\n\n{lines}" + DESC_TAIL, u.get('tags', []) + ['ピエロ', '雑学', '闇', '都市伝説', '10選', 'shorts']

def meta_long(u):
    lines = '\n'.join(f"{i + 1}. {it['head']}" for i, it in enumerate(u['items']))
    return u['yt_title'], f"{u['title']} 10選\n\n{lines}" + DESC_TAIL, u.get('tags', []) + ['ピエロ', '雑学', '闇', '都市伝説', '10選', '解説']

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
    yt = yt_client(); F = faces()
    shorts, longs = units('s'), units('l')
    for slot, kind, hh in (('A', 's', 12), ('L', 'l', 16), ('B', 's', 20)):
        if dd.get(slot, {}).get('video'): print('done', slot, dd[slot]); continue
        lst = shorts if kind == 's' else longs
        key = 'next_short' if kind == 's' else 'next_long'
        u = lst[st[key] % len(lst)]
        when = now.replace(hour=hh, minute=0, second=0, microsecond=0)
        out = os.path.join(WORK, f'{day}_{slot}_{u["id"]}.mp4')
        if kind == 's':
            build_short(u, out, F); t, d, tags = meta_short(u); thumb = None
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
    elif task == 'whoami': yt_client(); print('channel ok')
    print('elapsed', round(time.time() - t0), 's')
