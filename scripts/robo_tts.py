"""Robo lines with GPT-SoVITS (owner's voice) + robot-style filter. run from repo root."""
import os, sys, json, subprocess, argparse
ap = argparse.ArgumentParser(); ap.add_argument('eps', nargs='+'); g = ap.parse_args()
root = os.getcwd(); os.chdir('gsv'); sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), 'GPT_SoVITS'))
import soundfile as sf
from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
cfg = json.load(open(f'{root}/config/voice.json'))
tts = TTS(TTS_Config(f'{root}/scripts/tts_infer.yaml'))
REF = f"{root}/data/{cfg['ref']}.wav"; REF_T = cfg['ref_text']
aux = [f"{root}/data/{a}.wav" for a in cfg.get('aux_refs', [])]
for epid in g.eps:
    ep = json.load(open(f'{root}/episodes/{epid}.json')); out = f'{root}/vo/{epid}'; os.makedirs(out, exist_ok=True)
    for i, b in enumerate(ep['beats']):
        sp = b.get('say')
        if not sp or sp['who'] != 'robo': continue
        best = None
        for seed in (42, 7, 123):
            req = dict(text=sp['text'], text_lang='ja', ref_audio_path=REF, prompt_text=REF_T, prompt_lang='ja', aux_ref_audio_paths=aux,
                       top_k=15, top_p=1.0, temperature=0.9, text_split_method='cut0', batch_size=1, speed_factor=1.0, seed=seed,
                       parallel_infer=False, repetition_penalty=1.35)
            try:
                sr, audio = next(tts.run(req))
            except Exception as e:
                print('aux refs failed, retry without', e); req['aux_ref_audio_paths'] = []; aux.clear(); sr, audio = next(tts.run(req))
            dur = len(audio)/sr; exp = 0.13*len(sp['text'])+0.3
            score = abs(dur-exp)/exp
            if best is None or score < best[0]: best = (score, sr, audio)
            if score < 0.45: break
        raw = f'{out}/{i:02d}_raw.wav'; sf.write(raw, best[2], best[1])
        af = cfg['filter']
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', af, '-ar', '48000', '-ac', '1', f'{out}/{i:02d}.wav'])
        if r.returncode != 0:  # no rubberband in ffmpeg: resample-based pitch shift
            af2 = af.replace('rubberband=pitch=1.33', 'aresample=48000,asetrate=63840,aresample=48000,atempo=0.7519')
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', af2, '-ar', '48000', '-ac', '1', f'{out}/{i:02d}.wav'], check=True)
        print('robo', epid, i, round(len(best[2])/best[1], 2), 'score', round(best[0], 2), flush=True)
