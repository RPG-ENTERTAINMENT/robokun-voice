"""必要な1本ぶんのナレーションだけVOICEVOXで作る。 python voices.py <episode_id> -> voice/ep<id>_<k>.flac, voice/cta.flac
音声：VOICEVOX:春日部つむぎ（話者8）／ずんだもん（話者3）"""
import io, os, sys, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
VV = os.environ.get('VV_DIR', 'vv')
ort = Onnxruntime.load_once(filename=f'{VV}/onnxruntime/libvoicevox_onnxruntime.so')
syn = Synthesizer(ort, OpenJtalk(f'{VV}/dict'))
with VoiceModelFile.open(f'{VV}/models/0.vvm') as m: syn.load_voice_model(m)
SIDS = {'teacher': 8, 'cta': 8, 'boy': 3}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voice'); os.makedirs(OUT, exist_ok=True)
def make(name, txt, sid=8):
    q = syn.create_audio_query(txt, sid)
    q.speed_scale = 1.22; q.pitch_scale = 0.03; q.intonation_scale = 1.25; q.pre_phoneme_length = 0.02; q.post_phoneme_length = 0.05; q.volume_scale = 1.1
    x, sr = sf.read(io.BytesIO(syn.synthesis(q, sid)))
    idx = np.where(np.abs(x) > 0.01)[0]; x = x[max(0, idx[0] - 100): idx[-1] + 400] if len(idx) else x
    sf.write(f'{OUT}/{name}.flac', x, sr); return len(x) / sr
eid = int(sys.argv[1]); ep = next(e for e in episodes.EPISODES if e['id'] == eid)
if ep['type'] == 'story':
    for k, (spk, txt) in enumerate(ep['lines']): print(f"ep{eid}_{k} [{spk}] {make(f'ep{eid}_{k}', txt, SIDS[spk]):.2f}s", flush=True)
else:
    for k, txt in enumerate(ep['say']): print(f"ep{eid}_{k} {make(f'ep{eid}_{k}', txt):.2f}s", flush=True)
    print(f"cta {make('cta', episodes.CTA_SAY):.2f}s")
