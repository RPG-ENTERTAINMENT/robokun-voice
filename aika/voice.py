"""Make all voice lines + songs for one episode.  python voice.py episodes/epXX.json voice/epXX"""
import sys, os, io, json, wave, numpy as np
from voicevox_core import Note, Score, UserDictWord
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile, UserDict
VV = os.environ.get('VV_DIR', 'vv')
ort = Onnxruntime.load_once(filename=f'{VV}/onnxruntime/libvoicevox_onnxruntime.so')
oj = OpenJtalk(f'{VV}/dict')
ud = UserDict()
for surf, pron, acc in [('車中泊', 'シャチュウハク', 3), ('愛花', 'アイカ', 0)]:
    ud.add_word(UserDictWord(surface=surf, pronunciation=pron, accent_type=acc))
oj.use_user_dict(ud)
s = Synthesizer(ort, oj)
spec = json.load(open(sys.argv[1])); outd = sys.argv[2]; os.makedirs(outd, exist_ok=True)
SID = 0          # 四国めたん あまあま
SING_T, SINGER = 6000, 3000
need_song = any(isinstance(it, dict) and it.get('act') == 'song' for sc in spec['scenes'] for it in sc['lines'])
with VoiceModelFile.open(f'{VV}/models/0.vvm') as m: s.load_voice_model(m)
if need_song:
    with VoiceModelFile.open(f'{VV}/models/s0.vvm') as m: s.load_voice_model(m)
TPL = {'A': [[76, 76, 79, 81, 79, 76, 74, 76], [74, 74, 76, 79, 76, 74, 72]],
       'B': [[76, 79, 81, 84, 81, 79, 79], [81, 79, 76, 79, 76, 74, 72, 72]]}
LEN = {'A': [[1, 1, 1, 1, 1, 1, 1, 4], [1, 1, 1, 1, 1, 1, 5]], 'B': [[1, 1, 1, 1, 1, 1, 5], [1, 1, 1, 1, 1, 1, 1, 4]]}
FR, E = 93.75, 0.3
def f(sec): return max(1, round(sec * FR))
def save(name, x, sr):
    x = x / max(1e-6, np.abs(x).max()) * 0.9
    o = wave.open(f'{outd}/{name}.wav', 'wb'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((x * 32767).astype(np.int16).tobytes()); o.close()
    idx = np.nonzero(np.abs(x) > 0.02)[0]
    return {'dur': len(x) / sr, 'start': idx[0] / sr, 'end': idx[-1] / sr}
meta = {}
for si, sc in enumerate(spec['scenes']):
    for j, it in enumerate(sc['lines']):
        if isinstance(it, str): it = {'say': it}
        k = f's{si}_{j}'
        if 'say' in it:
            q = s.create_audio_query_from_kana(it['kana'], SID) if it.get('kana') else s.create_audio_query(it['say'], SID)
            q.speed_scale = 1.08; q.pitch_scale = 0.03; q.intonation_scale = 1.3
            q.pre_phoneme_length = 0.1; q.post_phoneme_length = 0.15
            print(k, q.kana if hasattr(q, 'kana') else '', flush=True)
            w = wave.open(io.BytesIO(s.synthesis(q, SID)))
        elif it.get('act') == 'song':
            tpl = it['song']; notes = [Note(f(0.3), '')]
            for p, ly in enumerate(it['lyrics']):
                assert len(ly) == len(TPL[tpl][p]), (k, p, ly)
                for mora, key, ln in zip(ly, TPL[tpl][p], LEN[tpl][p]): notes.append(Note(f(E * ln), mora, key=key))
                notes.append(Note(f(E * (1 if p == 0 else 2)), ''))
            sc_ = Score(notes); q = s.create_sing_frame_audio_query(sc_, SING_T)
            w = wave.open(io.BytesIO(s.frame_synthesis(q, SINGER)))
            print(k, 'song', ''.join(sum(it['lyrics'], [])), flush=True)
        else:
            continue
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
        meta[k] = save(k, x, w.getframerate())
json.dump(meta, open(f'{outd}/meta.json', 'w'), ensure_ascii=False, indent=1)
print('voice done', len(meta))
