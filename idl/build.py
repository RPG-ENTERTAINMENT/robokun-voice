"""Build 東京アイドルスクール アイドル講座 lesson videos (igc の仕組みを流用).  python idl/build.py 1 2 3 [--upload] [--still]
voice: VOICEVOX ずんだもん (VV_DIR), slides: slides.py, render: render.py, upload: YouTube (unlisted)."""
import os, sys, json, re, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); IGC = os.path.join(HERE, '..', 'igc')
sys.path.insert(0, HERE); sys.path.insert(1, IGC)
import slides
from episodes import EPS
WORK = os.environ.get('IDL_WORK', os.path.join(HERE, '..', 'idl_work')); os.makedirs(WORK, exist_ok=True)
STATE = os.path.join(HERE, 'state', 'videos.json')
args = [a for a in sys.argv[1:] if not a.startswith('--')]
nums = []
for a in args:
    if '-' in a: x, y = map(int, a.split('-')); nums += list(range(x, y + 1))
    else: nums.append(int(a))
UPLOAD = '--upload' in sys.argv; STILL = '--still' in sys.argv

def plain(t):  # the trial video used a plain (non-のだ) tone
    for a, b in [('なのだ！', 'だよ！'), ('なのだ。', 'だよ。'), ('のだ！', 'よ！'), ('のだ。', 'よ。'), ('のだ', 'よ')]: t = t.replace(a, b)
    return t
def say(t):  # reading fixes for the TTS
    t = plain(t)
    for a, b in [('第1回', '第いっかい'), ('第2回', '第にかい'), ('第3回', '第さんかい'), ('第4回', '第よんかい'), ('第5回', '第ごかい'), ('第6回', '第ろっかい'),
                 ('第7回', '第ななかい'), ('第8回', '第はちかい'), ('第9回', '第きゅうかい'), ('第10回', '第じゅっかい'), ('第11回', '第じゅういっかい'), ('第12回', '第じゅうにかい'),
                 ('第13回', '第じゅうさんかい'), ('第14回', '第じゅうよんかい'), ('第15回', '第じゅうごかい'), ('第16回', '第じゅうろっかい'), ('第17回', '第じゅうななかい'),
                 ('第18回', '第じゅうはちかい'), ('第19回', '第じゅうきゅうかい'), ('第20回', '第にじゅっかい'), ('全20回', 'ぜんにじゅっかい'), ('20回', 'にじゅっかい'),
                 ('PR', 'ピーアール'), ('DM', 'ディーエム'), ('SNS', 'エスエヌエス'), ('24時間', 'にじゅうよじかん'), ('300軒', 'さんびゃっけん'), ('1本', 'いっぽん'),
                 ('1枚', 'いちまい'), ('1行目', 'いちぎょうめ'), ('1秒', 'いちびょう'), ('1つ', 'ひとつ'), ('1杯', 'いっぱい'), ('10本', 'じゅっぽん'), ('5本', 'ごほん'),
                 ('3枚', 'さんまい'), ('10枚', 'じゅうまい'), ('5選', 'ごせん'), ('5つ', 'いつつ'), ('4つ', 'よっつ'), ('3つ', 'みっつ'), ('2つ', 'ふたつ'),
                 ('20代', 'にじゅうだい'), ('2択', 'にたく'), ('2本', 'にほん'), ('30秒', 'さんじゅうびょう'), ('3行', 'さんぎょう'), ('4行', 'よんぎょう'), ('1回', 'いっかい'),
                 ('週に1回', 'しゅうにいっかい'), ('何々', 'なになに'), ('名前', 'なまえ'), ('第1回', '第いっかい'), ('全10回', 'ぜんじゅっかい'), ('10回', 'じゅっかい'), ('TikTok', 'ティックトック'), ('Instagram', 'インスタグラム'), ('YouTube', 'ユーチューブ'), ('15秒', 'じゅうごびょう'), ('10秒', 'じゅうびょう'), ('5秒', 'ごびょう'), ('5回', 'ごかい'), ('10回', 'じゅっかい'), ('3回', 'さんかい'), ('1人', 'ひとり'), ('8つ', 'やっつ'), ('8カウント', 'エイトカウント'), ('全身', 'ぜんしん'), ('宣材', 'せんざい'), ('伸びしろ', 'のびしろ'), ('口角', 'こうかく')]:
        t = t.replace(a, b)
    return t

_syn = None
def synth():
    global _syn
    if _syn is None:
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        vv = os.environ.get('VV_DIR', os.path.join(HERE, '..', 'vv'))
        lib = (glob.glob(vv + '/onnxruntime/libvoicevox_onnxruntime.so*') + glob.glob(vv + '/voicevox_onnxruntime*/lib/libvoicevox_onnxruntime.so*'))[0]
        dic = (glob.glob(vv + '/dict') + glob.glob(vv + '/open_jtalk_dic*'))[0]
        _syn = Synthesizer(Onnxruntime.load_once(filename=lib), OpenJtalk(dic))
        model = (glob.glob(vv + '/models/0.vvm') + glob.glob(vv + '/0.vvm'))[0]
        with VoiceModelFile.open(model) as m: _syn.load_voice_model(m)
    return _syn

def tts(text, path):
    s = synth(); q = s.create_audio_query(text, 3)
    q.speed_scale = 1.08; q.intonation_scale = 1.25; q.output_sampling_rate = 48000; q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.12
    for a in q.accent_phrases:
        pm = a.pause_mora
        if pm is None: continue
        if isinstance(pm, dict): pm['vowel_length'] *= 0.8
        else: pm.vowel_length *= 0.8
    open(path, 'wb').write(s.synthesis(q, 3))

bg = os.path.join(WORK, 'classroom.png'); bgm = os.path.join(WORK, 'lofi.wav')
if not os.path.exists(bg): slides.classroom(bg)
if not os.path.exists(bgm): slides.lofi(bgm)
state = json.load(open(STATE)) if os.path.exists(STATE) else {}

def short(e): return e['title'].split('｜')[0]
for n in nums:
    e = [x for x in EPS if x['n'] == n][0]; d = os.path.join(WORK, f'id{n:02d}'); os.makedirs(d, exist_ok=True)
    beats, screen = [], {}
    for i, (text, kw, pose, sl, sfx) in enumerate(e['beats']):
        key = f'b{i:02d}'; img = os.path.join(d, f's{i:02d}.jpg'); slides.make(sl, img, seed=n * 7 + i)
        if not STILL or i < 3: tts(say(text), os.path.join(d, f'{i:02d}.wav'))
        beats.append(dict(key=key, say=dict(who='robo', text=plain(text))))
        sc = dict(img=img, pose=pose)
        if kw: sc['kw'] = kw.replace('{', '').replace('}', '')
        if sfx: sc['sfx'] = sfx
        if sl['t'] in ('cards',) and sl.get('hi') is not None: sc['fade'] = True
        if i == 0: sc.update(title=e['kt'], kicker=(f'アイドル講座 第{n}回' if n < 10 else 'アイドル講座 最終回'))
        if sl['t'] == 'hw': sc['pause'] = 0.6
        screen[key] = sc
    spec = dict(id=f'id{n:02d}', tag=f'東京アイドルスクール アイドル講座 第{n}回', bg=bg, bgm=bgm, bgm_vol=0.11, credit='VOICEVOX:ずんだもん', brand='東京アイドルスクール', beats=beats, screen=screen)
    sp = os.path.join(d, 'spec.json'); json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
    out = os.path.join(d, f'idol_{n:02d}.mp4')
    if STILL:
        if STILL: spec['beats'] = spec['beats'][:3]; json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
        subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), sp, d, out, '--still', '0', '9', '16'], check=True); continue
    subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), sp, d, out], check=True)
    thumb = out[:-4] + '_thumb.png'; subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), sp, d, out, '--still', '0'], check=True)
    os.replace(out + '.still_0.png', thumb)
    print('built', n, out, flush=True)
    if UPLOAD:
        if str(n) in state: print('already uploaded', n, state[str(n)]); continue
        meta = dict(title=f'アイドル講座 第{n}回｜{e["title"]}'[:100], privacy='unlisted', category='27',
                    description=f'東京アイドルスクール アイドル講座 第{n}回\n{e["desc"]}\n\n▼東京アイドルスクール\nhttps://www.rpgtokyo.com/idol/\n\nロボしずの声：VOICEVOX:ずんだもん\nBGM：オリジナル',
                    tags=['アイドル', 'アイドル講座', '東京アイドルスクール', 'ダンス', 'ボイトレ', 'ロボしず'])
        mp = os.path.join(d, 'meta.json'); json.dump(meta, open(mp, 'w'), ensure_ascii=False)
        r = subprocess.run([sys.executable, os.path.join(IGC, 'upload.py'), out, thumb, mp], capture_output=True, text=True); print(r.stdout, r.stderr[-2000:], flush=True)
        m = re.search(r'youtube ok (\S+)', r.stdout)
        if m:
            state[str(n)] = m.group(1); os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(state, open(STATE, 'w'), indent=1)
