"""Voice for one episode: Google Cloud TTS Chirp3-HD (ゆり=Leda +4 semitones, ロボしず=Fenrir + robot effect).
  python tts.py <episode.json> <outdir>  -> outdir/voice.wav, outdir/timing.json"""
import os, sys, json, base64, urllib.request, subprocess, io, wave
import numpy as np
SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
VOICE = {'ol': 'ja-JP-Chirp3-HD-Leda', 'robo': 'ja-JP-Chirp3-HD-Fenrir'}
OL_SEMI = 4
_key = None

def synth(text, who, rate=1.0):
    global _key
    if os.environ.get('HATENA_LOCAL_TTS'):   # offline fallback for local tests
        import pyopenjtalk
        x, sr = pyopenjtalk.tts(text, speed=1.1, half_tone=(1.0 if who == 'ol' else -1.5))
        return x.astype(np.float32) / 32768
    if _key is None:
        from secret import tts_key; _key = tts_key()
    body = {"input": {"text": text}, "voice": {"languageCode": "ja-JP", "name": VOICE[who]},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SR, "speakingRate": rate}}
    req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + _key,
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    for i in range(4):
        try:
            a = base64.b64decode(json.load(urllib.request.urlopen(req, timeout=60))['audioContent']); break
        except Exception as e:
            print('tts retry', i, e, flush=True)
            if i == 3: raise
    w = wave.open(io.BytesIO(a)); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

def trim(x):
    nz = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, nz[0] - 600): nz[-1] + 1800] if len(nz) else x
def ff(x, af):
    p = subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af', af, '-f', 'f32le', '-'],
                       input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32)
def pitch(x, semi):
    r = 2 ** (semi / 12); return ff(x, f'asetrate={int(SR * r)},aresample={SR},atempo={1 / r:.4f}')
def robotize(x, a=0.6):
    t = np.arange(len(x)) / SR; y = x * (1 - 0.3 * a + 0.3 * a * np.sin(2 * np.pi * 55 * t))
    d = int(0.006 * SR); y2 = y.copy(); y2[d:] += 0.45 * a * y[:-d]; return y2 / max(1, np.abs(y2).max() / 0.95)
def voice(text, who):
    x = trim(synth(text, who))
    if who == 'ol' and not os.environ.get('HATENA_LOCAL_TTS'): x = pitch(x, OL_SEMI)
    if who == 'robo': x = robotize(x)
    return x.astype(np.float32)

def main(ep_path, out):
    ep = json.load(open(ep_path)); os.makedirs(out, exist_ok=True)
    segs = []; chunks = []; t = 0.3
    for c in ep['title_chunks']:
        x = voice(c.replace('\n', ''), 'ol'); chunks.append({'text': c, 't': round(t, 3)})
        segs.append((t + 0.12, x)); t = t + 0.12 + len(x) / SR + 0.18
    intro = t + 0.7
    t = intro + 0.2; lines = []
    for ln in ep['lines']:
        x = voice(ln.get('say') or ln['text'].replace('\n', '、').replace('、、', '、'), ln['sp'])
        lines.append(dict(ln, s=round(t, 3), e=round(t + len(x) / SR, 3))); segs.append((t, x)); t += len(x) / SR + 0.3
    end = t + 1.0
    v = np.zeros(int(end * SR) + SR, np.float32)
    for s, x in segs: i = int(s * SR); v[i:i + len(x)] += x
    v = v[:int(end * SR)]
    w = wave.open(os.path.join(out, 'voice.wav'), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(v, -1, 1) * 32767).astype(np.int16).tobytes())
    json.dump({'intro': round(intro, 3), 'end': round(end, 3), 'chunks': chunks, 'lines': lines, 'sets': ep.get('sets')}, open(os.path.join(out, 'timing.json'), 'w'), ensure_ascii=False, indent=1)
    print('TTS OK', round(end, 2), 's')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
