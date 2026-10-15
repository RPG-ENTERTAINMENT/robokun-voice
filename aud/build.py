"""オーディション講座の動画を作る。python aud/build.py 1 [--still]
声: VOICEVOX ずんだもん（igc と同じ設定）、スライド: igc/slides.py ＋ atitle、描画: igc/render.py"""
import os, sys, json, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); IGC = os.path.join(HERE, '..', 'igc'); sys.path.insert(0, IGC); sys.path.insert(0, HERE)
os.environ.setdefault('IGC_ASSETS', os.path.join(HERE, '..', 'assets')); os.environ.setdefault('IGC_SPRITES', os.path.join(HERE, '..', 'assets', 'sp'))
import slides
from PIL import Image, ImageDraw
from episodes import EPS
WORK = os.environ.get('AUD_WORK', os.path.join(HERE, '..', 'aud_work')); os.makedirs(WORK, exist_ok=True)
STILL = '--still' in sys.argv
nums = [int(a) for a in sys.argv[1:] if not a.startswith('--')] or [1]
sys.argv = [sys.argv[0]]  # igc/build の関数だけ借りる
import importlib.util
spec_ = importlib.util.spec_from_file_location('igcb_funcs', os.path.join(IGC, 'build.py'))
src = open(os.path.join(IGC, 'build.py')).read().split("bg = os.path.join(WORK, 'classroom.png')")[0]
g = {'__file__': os.path.join(IGC, 'build.py'), '__name__': 'igcb'}; exec(compile(src, 'igc_build_head', 'exec'), g)
say, plain, tts = g['say'], g['plain'], g['tts']
def say2(t):
    for a, b in [('1つめ', 'ひとつめ'), ('2つめ', 'ふたつめ'), ('3つめ', 'みっつめ'), ('4つめ', 'よっつめ'), ('5つめ', 'いつつめ'), ('5つのこと', 'いつつのこと'),
                 ('背すじ', 'せすじ'), ('一言', 'ひとこと'), ('第1回', '第いっかい')]: t = t.replace(a, b)
    return say(t)

def atitle(sp, path, seed):
    im = slides.pastel(seed); d = ImageDraw.Draw(im); PW, PH = slides.PW, slides.PH
    cx, cy = PW - 300, PH // 2 - 10
    for r, a in [(330, 60), (260, 90), (190, 140)]: d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 236, 160, a))
    for k in range(9):  # spotlight rays
        an = -math.pi / 2 + (k - 4) * 0.22; d.polygon([(cx, cy), (cx + 900 * math.cos(an - 0.05), cy + 900 * math.sin(an - 0.05)), (cx + 900 * math.cos(an + 0.05), cy + 900 * math.sin(an + 0.05))], fill=(255, 245, 200))
    e = slides.emoji(sp['e'], 300); im.alpha_composite(e, (cx - e.width // 2, cy - e.height // 2))
    for j, e2 in enumerate(sp['around']):
        a = j * 2 * math.pi / len(sp['around']) - math.pi / 3; e3 = slides.emoji(e2, 110)
        im.alpha_composite(e3, (int(cx + 250 * math.cos(a) - e3.width // 2), int(cy + 250 * math.sin(a) - e3.height // 2)))
    im.convert('RGB').save(path, quality=92)

def make(sl, path, seed):
    if sl['t'] == 'atitle': return atitle(sl, path, seed)
    return slides.make(sl, path, seed=seed)

bg = os.path.join(WORK, 'classroom.png'); bgm = os.path.join(WORK, 'lofi.wav')
if not os.path.exists(bg): slides.classroom(bg)
if not os.path.exists(bgm): slides.lofi(bgm)
for n in nums:
    e = [x for x in EPS if x['n'] == n][0]; d = os.path.join(WORK, f'aud{n:02d}'); os.makedirs(d, exist_ok=True)
    beats, screen = [], {}
    for i, (text, kw, pose, sl, sfx) in enumerate(e['beats']):
        key = f'b{i:02d}'; img = os.path.join(d, f's{i:02d}.jpg'); make(sl, img, seed=n * 11 + i)
        tts(say2(text), os.path.join(d, f'{i:02d}.wav'))
        beats.append(dict(key=key, say=dict(who='robo', text=plain(text))))
        sc = dict(img=img, pose=pose)
        if kw: sc['kw'] = kw
        if sfx: sc['sfx'] = sfx
        if sl['t'] == 'cards' and sl.get('hi') is not None: sc['fade'] = True
        if i == 0: sc.update(title=e['kt'], kicker=f'オーディション講座 第{n}回')
        if sl['t'] == 'hw': sc['pause'] = 0.6
        screen[key] = sc
    short = e['title'].replace('知らないと損！', '')
    spec = dict(id=f'aud{n:02d}', tag=f'オーディション講座 第{n}回', bg=bg, bgm=bgm, bgm_vol=0.11, credit='VOICEVOX:ずんだもん', beats=beats, screen=screen)
    sp = os.path.join(d, 'spec.json'); json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
    out = os.path.join(d, f'audition_{n:02d}.mp4')
    if STILL:
        subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out, '--still', '0', '12', '20', '40'], check=True); continue
    subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out], check=True)
    subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out, '--still', '0'], check=True)
    os.replace(out + '.still_0.png', out[:-4] + '_thumb.png'); print('built', out)
