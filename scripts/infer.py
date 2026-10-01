import os, sys, json, traceback
import numpy as np, soundfile as sf
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), 'GPT_SoVITS'))
from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
cfg = TTS_Config('../scripts/tts_infer.yaml')
print(cfg)
tts = TTS(cfg)
REF = '../data/12.wav'
REF_T = 'ぼくのからだはいしでできているけど、こころはやわらかいよ。'
lines = json.load(open('../jobs/lines.json'))
os.makedirs('../out', exist_ok=True)
for k, text in lines.items():
    try:
        req = dict(text=text, text_lang='ja', ref_audio_path=REF, prompt_text=REF_T, prompt_lang='ja',
                   top_k=15, top_p=1.0, temperature=1.0, text_split_method='cut0', batch_size=1,
                   speed_factor=1.0, seed=42, parallel_infer=False, repetition_penalty=1.35)
        for sr, audio in tts.run(req):
            sf.write(f'../out/{k}.wav', audio, sr)
            print('ok', k, len(audio)/sr)
    except Exception:
        traceback.print_exc()
