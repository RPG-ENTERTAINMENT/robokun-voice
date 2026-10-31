"""大道芸講座（大道芸専門アカデミー @daidogeisenmon の横動画）を作る。python daido/lesson/build.py 1,2 [--upload]
--upload なし: GitHub release「daido-lesson」に置くだけ（確認用）。--upload: チャンネルに公開アップ（daido/rt.enc の接続を使う）。
声: VOICEVOX ずんだもん、スライド: igc/slides.py ＋ atitle、描画: igc/render.py（aud/build.py と同じ作り）"""
import os, sys, json, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); IGC = os.path.join(HERE, '..', '..', 'igc'); sys.path.insert(0, IGC); sys.path.insert(0, HERE)
os.environ.setdefault('IGC_ASSETS', os.path.join(HERE, '..', '..', 'assets')); os.environ.setdefault('IGC_SPRITES', os.path.join(HERE, '..', '..', 'assets', 'sp'))
import slides
from PIL import Image, ImageDraw
from episodes import EPS
WORK = os.environ.get('DG_WORK', os.path.join(HERE, '..', '..', 'daido_lesson_work')); os.makedirs(WORK, exist_ok=True)
STILL = '--still' in sys.argv; UPLOAD = '--upload' in sys.argv
STATE = os.path.join(HERE, '..', 'state', 'lessons.json')
nums = []
for a in [a for a in sys.argv[1:] if not a.startswith('--')]:
    for part in a.split(','):
        if '-' in part: x, y = map(int, part.split('-')); nums += list(range(x, y + 1))
        else: nums.append(int(part))
nums = nums or [1]
sys.path.insert(0, IGC)
sys.argv = [sys.argv[0]]  # igc/build の関数だけ借りる
import importlib.util
spec_ = importlib.util.spec_from_file_location('igcb_funcs', os.path.join(IGC, 'build.py'))
src = open(os.path.join(IGC, 'build.py')).read().split("bg = os.path.join(WORK, 'classroom.png')")[0]
g = {'__file__': os.path.join(IGC, 'build.py'), '__name__': 'igcb'}; exec(compile(src, 'igc_build_head', 'exec'), g)
say, plain, tts = g['say'], g['plain'], g['tts']
def say2(t):
    for a, b in [('1つめ', 'ひとつめ'), ('2つめ', 'ふたつめ'), ('3つめ', 'みっつめ'), ('4つめ', 'よっつめ'), ('5つめ', 'いつつめ'), ('5つのこと', 'いつつのこと'),
                 ('15分', 'じゅうごふん'), ('5分', 'ごふん'), ('10秒', 'じゅうびょう'), ('1種類', 'ひとしゅるい'), ('1曲', 'いっきょく'), ('3本', 'さんぼん'), ('お手玉', 'おてだま'), ('投げ銭', 'なげせん'), ('宣材', 'せんざい'), ('見せ場', 'みせば'), ('一番', 'いちばん')]: t = t.replace(a, b)
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
FAILED = []
import re, base64, hashlib
URL = 'https://rpgtokyo.com/daidogei/'; LINE = 'https://lin.ee/zuMn2H1'
def yt_token():
    from cryptography.fernet import Fernet
    csec = os.environ['YT_CLIENT_SECRET']
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(csec.encode()).digest())).decrypt(open(os.path.join(HERE, '..', 'rt.enc'), 'rb').read()).decode()
built = []
for n in nums:
    e = [x for x in EPS if x['n'] == n][0]; d = os.path.join(WORK, f'dg{n:02d}'); os.makedirs(d, exist_ok=True)
    beats, screen = [], {}
    for i, (text, kw, pose, sl, sfx) in enumerate(e['beats']):
        key = f'b{i:02d}'; img = os.path.join(d, f's{i:02d}.jpg'); make(sl, img, seed=n * 11 + i)
        tts(say2(text), os.path.join(d, f'{i:02d}.wav'))
        beats.append(dict(key=key, say=dict(who='robo', text=plain(text))))
        sc = dict(img=img, pose=pose)
        if kw: sc['kw'] = kw
        if sfx: sc['sfx'] = sfx
        if sl['t'] == 'cards' and sl.get('hi') is not None: sc['fade'] = True
        if i == 0: sc.update(title=e['kt'], kicker=f'大道芸講座 第{n}回')
        if sl['t'] == 'hw': sc['pause'] = 0.6
        screen[key] = sc
    spec = dict(id=f'dg{n:02d}', tag=f'大道芸講座 第{n}回｜大道芸専門アカデミー', bg=bg, bgm=bgm, bgm_vol=0.11, credit='VOICEVOX:ずんだもん', beats=beats, screen=screen)
    sp = os.path.join(d, 'spec.json'); json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
    out = os.path.join(d, f'daidogei_lesson_{n:02d}.mp4')
    if STILL:
        subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out, '--still', '0', '12', '40', '90'], check=True); continue
    subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out], check=True)
    subprocess.run([sys.executable, os.path.join(IGC, 'render.py'), sp, d, out, '--still', '0'], check=True)
    thumb = out[:-4] + '_thumb.png'; os.replace(out + '.still_0.png', thumb); built += [out, thumb]
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout or 0)
    print('built', out, f'{dur:.1f}s', flush=True)
    if UPLOAD:
        state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        if str(n) in state: print('already uploaded', n, state[str(n)]); continue
        meta = dict(title=f'{e["title"]}｜大道芸講座 第{n}回'[:100], privacy='public', category='27',
                    description=(f'大道芸講座 第{n}回\n{e["desc"]}\n\n'
                                 '━━━━━━━━━━\n🎪 大道芸専門アカデミー 生徒募集中\n'
                                 '・静岡大道芸の元出演者が、毎週オンラインであなたのショーをチェック\n'
                                 '・全国どこからでも、好きな時間に受講OK\n・仕事につなげる就職コースあり\n・月々25,000円から\n\n'
                                 f'▶ 詳しく・無料相談：{URL}\n▶ LINEで相談：{LINE}\n━━━━━━━━━━\n\n'
                                 '#大道芸 #大道芸人 #ジャグリング #パフォーマー #大道芸専門アカデミー\n\n'
                                 'ロボしずの声：VOICEVOX:ずんだもん\nBGM：オリジナル\n制作：株式会社RPGエンターテイメント'),
                    tags=['大道芸', '大道芸人', '大道芸人になるには', 'ジャグリング', 'パフォーマー', '大道芸専門アカデミー', '大道芸講座'], min_dur=120)
        mp = os.path.join(d, 'meta.json'); json.dump(meta, open(mp, 'w'), ensure_ascii=False)
        env = dict(os.environ, YT_REFRESH_TOKEN=yt_token())
        r = subprocess.run([sys.executable, os.path.join(IGC, 'upload.py'), out, thumb, mp], capture_output=True, text=True, env=env); print(r.stdout, r.stderr[-2000:], flush=True)
        m = re.search(r'youtube ok (\S+)', r.stdout)
        if m:
            state[str(n)] = m.group(1); os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(state, open(STATE, 'w'), indent=1)
        else: FAILED.append(n)
if built and not UPLOAD and not STILL:
    subprocess.run(['gh', 'release', 'delete', 'daido-lesson', '-y', '--cleanup-tag'])
    subprocess.run(['gh', 'release', 'create', 'daido-lesson', *built, '--title', '大道芸講座 確認用', '--notes', ' '.join(map(str, nums)), '--prerelease'], check=True)
if FAILED: print('upload failed for', FAILED); sys.exit(1)
