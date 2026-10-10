"""Data-driven episode module for the OLあいか channel.
render.py / audio.py import this as EP (env EP=ep_engine). It reads:
  AIKA_SPEC  = episodes/epXX.json   (the script)
  AIKA_VOICE = voice/epXX           (wav files + meta.json made by voice.py)
"""
import os, json, math, random
from PIL import Image, ImageDraw, ImageFilter

SPEC = json.load(open(os.environ['AIKA_SPEC']))
VOICE_DIR = os.environ['AIKA_VOICE']
_META = json.load(open(f'{VOICE_DIR}/meta.json'))

FPS = 30
SPRITE_DIR = 'assets'
K = {'bwave': 2.9, 'bwalk': 1.73, 'bmic': 1.88, 'bguitar': 1.65, 'bspoon': 1.65}
HEAD_ANCHOR = {'bwave', 'bwalk'}
SIT = {'bguitar', 'bspoon'}
CHAIR = 'chair_front'
TABLES = {}
TSHIFT = -100
TW = 0.32
BUBBLE = []
TITLE = (SPEC['tag'], SPEC['t1'], SPEC['t2'])
ENDC = (SPEC['end'][0], SPEC['end'][1], 'フォローして いっしょに旅しよ♪')
STEAMY = {'soup', 'udon', 'nabe'}

def wrap(s, n=14):
    if '\n' in s or len(s) <= n: return s
    cands = [i for i, ch in enumerate(s) if ch in '、。！？ 　…'] or list(range(len(s)))
    i = min(cands, key=lambda i: abs(i - len(s) / 2))
    a, b = s[:i + 1].strip(), s[i + 1:].strip()
    return a + '\n' + b if b else a

# ---------------------------------------------------------------- timeline
VO, SUB, ONO, BURST, EV = {}, {}, [], [], []
SCN = []        # dicts: s0, s1, bg, pose, food, chapter, items[(t0, t1, kind, data)]
TRANS = []
PINK = '#ff6f91'
cur = 0.15
chap = 0
for si, sc in enumerate(SPEC['scenes']):
    if si > 0:
        T = cur + 0.25; TRANS.append(T); s0 = T; cur = T + 0.85
    else:
        s0 = 0.0
    pose = sc.get('pose', 'open' if si == 0 else 'stand')
    if sc.get('type') == 'end': pose = 'end'
    if pose == 'walk': cur = max(cur, s0 + 2.5)
    ch = None
    if sc.get('chapter'):
        chap += 1; ch = (str(chap), sc['chapter'])
        BURST.append((s0 + 0.4, 540, 300, 'star', 8))
    S = {'s0': s0, 'bg': sc.get('bg', 'sun'), 'pose': pose, 'food': sc.get('food'), 'chapter': ch, 'items': []}
    for j, it in enumerate(sc['lines']):
        if isinstance(it, str): it = {'say': it}
        if 'say' in it:
            k = f's{si}_{j}'; m = _META[k]
            VO[k] = cur; SUB[k] = wrap(it.get('sub', it['say']).replace('、', ' ').replace('しゃちゅうはく', '車中泊'))
            S['items'].append((cur, cur + m['end'], 'say', k)); cur += m['end'] + 0.32
        elif it.get('act') == 'eat':
            t0 = cur; S['items'].append((t0, t0 + 2.5, 'eat', it))
            ONO.append((t0 + 0.75, t0 + 1.15, 'ぱくっ', 270, 760, PINK, 70))
            ONO.append((t0 + 1.1, t0 + 2.3, it.get('ono', 'もぐもぐ'), 260, 800, PINK, 66))
            ONO.append((t0 + 2.3, t0 + 4.2, it.get('yum', 'おいしい♡'), 270, 700, '#ff4f7f', 70))
            BURST.append((t0 + 2.3, 600, 800, 'heart', 9)); EV.append(('eat', t0, S['food']))
            cur += 2.6
        elif it.get('act') == 'song':
            k = f's{si}_{j}'; m = _META[k]; t0 = cur
            VO[k] = t0 + 1.2; SUB[k] = it['sub']
            t1 = t0 + 1.2 + m['end'] + 0.5
            S['items'].append((t0, t1, 'song', it)); EV.append(('song', t0 + 1.2, it['song'], pose))
            cur = t1 + 0.2
            if pose == 'mic':
                S['items'].append((cur, cur + 1.6, 'jump', it)); ONO.append((cur, cur + 2.0, 'イェーイ！', 540, 560, '#ff7a3d', 96))
                BURST.append((cur, 540, 700, 'star', 16)); EV.append(('applause', cur)); cur += 1.8
        elif it.get('act') == 'jump':
            S['items'].append((cur, cur + 1.6, 'jump', it))
            ONO.append((cur, cur + 1.9, it.get('ono', 'イェーイ！'), 540, 560, '#ff7a3d', 92))
            BURST.append((cur, 540, 800, 'star', 12)); EV.append(('sparkle', cur)); cur += 1.7
        elif it.get('act') == 'drive':
            S['items'].append((cur, cur + 2.2, 'drive', it))
            ONO.append((cur, cur + 2.1, 'ブルルン♪', 540, 560, '#ff7a3d', 88)); EV.append(('drive', cur)); cur += 2.3
        elif 'ono' in it:
            ONO.append((cur, cur + 2.0, it['ono'], it.get('x', 270), it.get('y', 560), it.get('c', PINK), it.get('size', 64)))
            EV.append(('pop', cur))
    S['s1'] = cur
    SCN.append(S)
END_T = SCN[-1]['s0']
FLASH = [END_T]
BURST.append((END_T, 540, 900, 'star', 14)); BURST.append((0.4, 540, 820, 'star', 10))
DUR = min(175.0, round(SCN[-1]['s1'] + 2.8, 1))   # Shorts allow up to 3 min
SCN[-1]['s1'] = DUR
for a, b in zip(SCN, SCN[1:]): a['s1'] = b['s0']
SCENES = [(S['s0'], S['s1'], S['bg'], S['chapter']) for S in SCN]
FOODS = sorted({S['food'] for S in SCN if S['food']})
SONGS = [e for e in EV if e[0] == 'song']
BGM_MUTE = [(e[1] - 1.4, e[1] + _META[[k for k, v in VO.items() if abs(v - e[1]) < 1e-6][0]]['end'] + 0.6) for e in SONGS]

def scene_at(t):
    for S in SCN:
        if S['s0'] <= t < S['s1']: return S
    return SCN[-1]
def item_at(S, t):
    for it in S['items']:
        if it[0] <= t < it[1]: return it
    return None

def table_kind(t):
    S = scene_at(t)
    return S['food'] if S['pose'] == 'eat' else None

def tint(t):
    return (210, 196, 206) if scene_at(t)['bg'] == 'night' else None

# ---------------------------------------------------------------- poses
def char_state(t, mouth, cyc):
    S = scene_at(t); it = item_at(S, t); pose = S['pose']
    dx = dy = 0.0; kind = it[2] if it else None; a = t - it[0] if it else 0
    pk = f'{S["s0"]:.1f}{kind}{it[0] if it else 0:.1f}'
    if kind == 'jump':
        if pose == 'mic': return 'bmic_04', 0, -30 * abs(math.sin(a * math.pi * 1.6)) * max(0, 1 - a / 1.6), pk, 0
        n = 'bwave_%02d' % cyc([12, 13, 14, 15], 6, t, it[0])
        return n, 0, -70 * abs(math.sin(a * math.pi * 1.5)), pk, 0
    if kind == 'drive':
        return 'bwave_%02d' % cyc([8, 9, 10, 11], 4, t, it[0]), 0, -12 * abs(math.sin(a * math.pi * 2)), pk, 0
    if pose == 'open':
        if kind == 'say' and it is S['items'][0]: return 'bwave_%02d' % cyc([4, 5, 6, 7], 5, t), 0, 0, 'o1', 0
        return 'bwave_%02d' % cyc([8, 9, 10, 11], 4, t, S['items'][0][1]), 0, -12 * abs(math.sin(t * math.pi * 2)), 'o2', 0
    if pose == 'end':
        if kind == 'say': return 'bwave_%02d' % cyc([4, 5, 6, 7, 6, 5], 5, t, S['s0']), 0, 0, 'e1', 0
        return 'bwave_%02d' % cyc([12, 13, 14, 15], 5, t, S['s0']), 0, -40 * abs(math.sin((t - S['s0']) * math.pi * 1.25)), 'e2', 0
    if pose == 'walk' and t < S['s0'] + 2.4:
        p = (t - S['s0']) / 2.4
        return 'bwalk_%02d' % cyc([0, 1, 2, 3], 6.5, t, S['s0']), -460 * (1 - p) ** 1.4, -8 * abs(math.sin((t - S['s0']) * 6.5 / 2 * math.pi)), 'walk', 0
    if pose in ('stand', 'walk'):
        if kind == 'say': return ('bwave_02' if mouth(t) else 'bwave_00'), 0, 0, 'st' + pk, 0
        return 'bwave_%02d' % cyc([0, 0, 0, 1, 0, 3], 1.6, t, S['s0']), 0, 0, 'si', 0
    if pose == 'mic':
        if kind == 'song':
            return 'bmic_%02d' % cyc([1, 4, 6, 2, 5, 7, 0, 3], 2.2, t, it[0]), 0, -8 * abs(math.sin((t - it[0]) / 0.6 * math.pi)), pk, 0
        if kind == 'say': return 'bmic_%02d' % cyc([0, 2, 3, 7], 2, t, it[0]), 0, 0, pk, 0
        return 'bmic_%02d' % cyc([0, 3], 1.5, t, S['s0']), 0, 0, 'mi', 0
    if pose == 'guitar':
        if kind == 'song':
            return 'bguitar_%02d' % cyc([1, 5, 0, 2, 7, 3, 4, 6], 2.5, t, it[0]), 0, -5 * abs(math.sin((t - it[0]) / 0.6 * math.pi)), pk, 0
        if kind == 'say': return ('bguitar_00' if mouth(t) else 'bguitar_03'), 0, 0, pk, 0
        return 'bguitar_%02d' % cyc([0, 4, 3], 1.5, t, S['s0']), 0, 0, 'gi', 0
    if pose == 'eat':
        if kind == 'eat':
            seq = [(0.25, 0), (0.55, 3), (0.85, 1), (1.2, 2)]
            for lim, f in seq:
                if a < lim: return f'bspoon_{f:02d}', 0, 0, pk + str(f), 0
            if a < 2.2: return 'bspoon_%02d' % cyc([4, 2], 4, t, it[0] + 1.2), 0, 0, pk + 'm', 0
            return 'bspoon_05', 0, 0, pk + 'y', 0
        if kind == 'say': return ('bspoon_05' if mouth(t) else 'bspoon_07'), 0, 0, pk, 0
        return 'bspoon_00', 0, 0, 'ei', 0
    return 'bwave_00', 0, 0, 'x', 0


# ---------------------------------------------------------------- visuals
def draw_back(canvas, t, R):
    S = scene_at(t); it = item_at(S, t)
    if S['pose'] == 'mic' and it and it[2] in ('song', 'jump'):
        k = min(1, (t - it[0]) / 0.6) if it[2] == 'song' else 1
        lay = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for i, c in enumerate([(255, 120, 180), (120, 200, 255), (255, 230, 120)]):
            sx = 220 + i * 320; ang = math.sin(t * (0.9 + 0.25 * i) + i * 2) * 0.45
            ex = 540 + 520 * math.sin(ang + (i - 1) * 0.35)
            d.polygon([(sx - 14, 300), (sx + 14, 300), (ex + 150, 1440), (ex - 150, 1440)], fill=c + (int(60 * k),))
            d.ellipse([ex - 170, 1380, ex + 170, 1460], fill=c + (int(80 * k),))
        canvas.alpha_composite(lay.filter(ImageFilter.GaussianBlur(18)))

def draw_top(canvas, t, R):
    S = scene_at(t); it = item_at(S, t)
    if S['pose'] in ('guitar', 'mic') and not (it and it[2] == 'say'):
        ox, oy = (760, 1050) if S['pose'] == 'guitar' else (700, 900)
        rnd = random.Random(int(S['s0']))
        for i in range(10 if it and it[2] == 'song' else 5):
            ph = ((t - S['s0']) * 0.45 + i / 10) % 1
            x = ox + rnd.uniform(-160, 160) + 40 * math.sin(t * 2 + i); y = oy - ph * 650
            col = ['#ff6f91', '#5bb8e8', '#ffb43d', '#7ccf7c'][i % 4]
            al = min(1, ph * 5) * min(1, (1 - ph) * 3)
            R.paste_scaled(canvas, R.text_img('♪', 64, col, '#ffffff', 8), x, y, 0.7 + 0.3 * ((i * 7) % 3) / 2, rot=15 * math.sin(t * 3 + i), alpha=al)

def cam_shake(t):
    for e in EV:
        if e[0] == 'drive' and e[1] <= t < e[1] + 2.2:
            a = min(1, (t - e[1]) / 0.3) * min(1, (e[1] + 2.2 - t) / 0.4)
            return 7 * a * math.sin(t * 57), 5 * a * math.sin(t * 43 + 1)
    return 0, 0


# ---------------------------------------------------------------- audio
_PRESETS = [
    {'bpm': 100, 'transpose': 0, 'prog': ['C', 'Am', 'F', 'G'],
     'mel': [[76, None, 79, None, 81, 79, 76, None], [72, None, 76, None, 74, 72, 69, None],
             [69, 72, 77, None, 76, 74, 72, None], [74, None, 71, 74, 79, None, None, None]] * 2},
    {'bpm': 92, 'transpose': 5, 'prog': ['C', 'G', 'Am', 'Em', 'F', 'C', 'F', 'G'],
     'mel': [[72, None, 74, 76, None, 79, 76, None], [74, None, 71, None, 67, None, None, None],
             [69, 72, 76, None, 74, 72, 69, None], [71, None, 67, None, 64, None, None, None],
             [65, 69, 72, None, 77, None, 76, 74], [72, None, 76, None, 79, None, None, None],
             [77, 76, 74, 72, 69, None, 72, None], [74, None, None, None, 79, None, None, None]]},
    {'bpm': 108, 'transpose': 2, 'prog': ['C', 'F', 'G', 'C', 'Am', 'F', 'G', 'G'],
     'mel': [[67, 72, None, 72, 74, None, 76, None], [77, None, 76, 74, 72, None, 69, None],
             [71, None, 74, None, 79, None, 77, 76], [76, None, None, None, 72, None, None, None],
             [69, 72, 76, None, 76, 74, 72, None], [69, None, 72, None, 77, None, 76, None],
             [74, None, 76, 74, 71, None, 67, None], [71, None, 74, None, 77, None, 79, None]]},
]
BGM = _PRESETS[SPEC.get('bgm', int(SPEC['id'][2:]) % 3)]
CHORDS = {'A': ['C', 'F', 'C', 'G', 'C', 'C', 'G', 'C', 'G', 'C', 'C', 'C'],
          'B': ['C', 'F', 'F', 'G', 'G', 'G', 'F', 'C', 'C', 'G', 'C', 'C']}

def sfx_events(A):
    import numpy as np
    add, sfx = A.add, A.sfx
    for T0 in TRANS: add(sfx, A.whoosh(0.6), T0 - 0.35, 0.35)
    for S in SCN:
        if S['chapter']: add(sfx, A.pop(500, 1500), S['s0'] + 0.35, 0.35); add(sfx, A.sparkle(), S['s0'] + 0.4, 0.18)
        if S['pose'] == 'walk':
            tt = S['s0'] + 0.1
            while tt < S['s0'] + 2.4: add(sfx, A.step(0.8), tt, 0.22); tt += 0.31
        kind = {'sun': None, 'rain': 'rain', 'snow': 'snow', 'night': 'crickets'}[S['bg']]
        if kind: add(sfx, A.amb(max(0, S['s0'] - 0.3), min(A.DUR, S['s1'] + 0.3), kind), max(0, S['s0'] - 0.3), {'rain': 0.11, 'snow': 0.07, 'crickets': 0.09}[kind])
        else:
            r = random.Random(int(S['s0'] * 10)); tt = S['s0'] + 0.8
            while tt < S['s1'] - 0.5: add(sfx, A.bird(), tt, 0.09); tt += r.uniform(2.5, 4.5)
    for o in ONO: add(sfx, A.pop(700, 1200, 0.09), o[0], 0.2)
    add(sfx, A.sparkle(), 0.35, 0.22); add(sfx, A.sparkle(), END_T, 0.28)
    CH = {'C': [48, 55, 60, 64, 67, 72], 'F': [41, 53, 57, 60, 65, 69], 'G': [43, 50, 55, 59, 62, 67], 'Am': [45, 52, 57, 60, 64, 69]}
    def strum(t0, ch, g, up=False):
        for j, m in enumerate(CH[ch][::-1] if up else CH[ch]): add(sfx, A.pl(m, 1.4), t0 + j * 0.014, g)
    for e in EV:
        if e[0] == 'eat':
            t0, food = e[1], e[2]
            add(sfx, A.pop(300, 900, 0.1), t0 + 0.75, 0.4)
            if food in STEAMY: add(sfx, A.slurp(0.5), t0 + 0.85, 0.3)
            for tt in np.arange(t0 + 1.15, t0 + 2.2, 0.21): add(sfx, A.munch(), tt, 0.3)
            add(sfx, A.sparkle(), t0 + 2.3, 0.26)
        elif e[0] == 'song':
            start = e[1] + 0.3; chords = CHORDS[e[2]]
            strum(start - 1.2, 'C', 0.16); strum(start - 0.6, 'G', 0.16)
            for i, ch in enumerate(chords):
                strum(start + i * 0.6, ch, 0.16); strum(start + i * 0.6 + 0.3, ch, 0.09, up=True)
            strum(start + len(chords) * 0.6, 'C', 0.18)
        elif e[0] == 'applause':
            rng = np.random.default_rng(9)
            for k in range(70): add(sfx, A.noise_hit(0.05, 900, 5000, 0.01), e[1] + rng.uniform(0, 1.8), 0.12 * rng.uniform(0.4, 1))
        elif e[0] == 'drive':
            add(sfx, A.rumble(2.0), e[1], 0.55)
        elif e[0] in ('sparkle',):
            add(sfx, A.sparkle(), e[1], 0.26)
            for tt in [0, 0.33, 0.67, 1.0]: add(sfx, A.boing(0.3), e[1] + tt, 0.16)
