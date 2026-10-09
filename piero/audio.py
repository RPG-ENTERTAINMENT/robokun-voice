"""Audio for piero videos: scary TTS voice, music-box BGM (the registered 2-min track), SFX, mix."""
import numpy as np, subprocess, os
from scipy.io import wavfile
from scipy.signal import fftconvolve
SR = 48000

def tts(text, speed=1.05):
    import pyopenjtalk
    x, sr = pyopenjtalk.tts(text, speed=speed, half_tone=-3.0)
    x = x.astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
    nz = np.nonzero(np.abs(x) > 0.01)[0]
    if len(nz) == 0: return np.zeros(int(0.3 * SR), np.float32)
    return x[max(0, nz[0] - 480):nz[-1] + 2400]

def build_voice(texts, gaps, lead=0.6, tail=1.5, speed=1.05):
    """texts[i] spoken, then gaps[i] seconds of silence. returns (voice, segs[(s,e)], total)"""
    parts, segs, t = [], [], lead
    for tx, gp in zip(texts, gaps):
        x = tts(tx, speed); segs.append((t, t + len(x) / SR)); parts.append((t, x)); t += len(x) / SR + gp
    total = t + tail
    v = np.zeros(int(total * SR) + SR, np.float32)
    for s, x in parts: v[int(s * SR):int(s * SR) + len(x)] += x
    v = v[:int(total * SR)]
    v /= (np.abs(v).max() + 1e-9) * 1.1
    return v, segs, total

def write(path, x): wavfile.write(path, SR, np.clip(x, -1, 1).astype(np.float32))

def voice_fx(dry, out):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', dry, '-filter_complex',
        '[0]asplit=3[a][b][c];[b]asetrate=48000*0.5,aresample=48000,atempo=2.0,volume=0.45[low];'
        '[c]asetrate=48000*0.94,aresample=48000,atempo=1.0638,volume=0.35,adelay=18[thick];'
        '[a][low][thick]amix=inputs=3:normalize=0,lowpass=f=6500,highpass=f=70,'
        'aecho=0.8:0.6:45|110|190:0.22|0.14|0.08,acompressor=threshold=-18dB:ratio=3,volume=1.6[o]',
        '-map', '[o]', '-ar', str(SR), out], check=True)

def envelope(voice, fps, nf):
    hop = SR // fps
    env = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(voice) else 0 for i in range(nf + 2)])
    env = env / (env.max() + 1e-9)
    return np.maximum(env, np.r_[0, env[:-1]] * 0.6)

# ---------------------------------------------------------------- music box (registered track, 120 s)
def musicbox(path):
    if os.path.exists(path): return path
    sr = SR; bpm = 126; beat = 60 / bpm; bar = 3 * beat
    rng = np.random.default_rng(5); TOTAL = 120.0; N = int((TOTAL + 3) * sr)
    out = np.zeros(N, np.float32)
    def mf(n): return 440 * 2 ** ((n - 69) / 12)
    def note(t0, midi, vel=0.5, dur=1.6):
        i = int(t0 * sr); n = int(dur * sr); tt = np.arange(n) / sr
        if i >= N: return
        f = mf(midi) * (1 + 0.004 * np.sin(2 * np.pi * 0.7 * (t0 + tt)))
        ph = 2 * np.pi * np.cumsum(f) / sr
        s = (np.sin(ph) * np.exp(-tt * 2.2) + 0.35 * np.sin(2 * ph) * np.exp(-tt * 4) + 0.18 * np.sin(5.4 * ph) * np.exp(-tt * 9) + 0.1 * np.sin(9.1 * ph) * np.exp(-tt * 16))
        s *= np.minimum(1, tt / 0.002); e = min(N, i + n); out[i:e] += vel * s[:e - i]
    A_CH = [[45, 57, 60, 64], [45, 57, 60, 64], [52, 56, 59, 64], [52, 56, 59, 62], [45, 57, 60, 64], [53, 57, 60, 65], [52, 56, 59, 64], [45, 57, 60, 64]]
    B_CH = [[53, 57, 60, 65], [48, 55, 60, 64], [50, 57, 62, 65], [52, 56, 59, 64], [53, 57, 60, 65], [48, 55, 60, 64], [46, 58, 62, 65], [52, 56, 59, 64]]
    A_MEL = [(76, 1), (72, 1), (69, 1), (71, 1.5), (72, .5), (71, 1), (68, 1), (64, 1), (68, 1), (69, 2), (None, 1),
             (76, 1), (77, 1), (76, 1), (75, 1.5), (76, .5), (72, 1), (71, 1), (68, 1), (71, 1), (69, 3)]
    B_MEL = [(81, 1.5), (79, .5), (77, 1), (76, 2), (72, 1), (74, 1.5), (76, .5), (77, 1), (76, 3),
             (81, 1), (80, 1), (81, 1), (77, 1.5), (76, .5), (74, 1), (72, 1), (71, 1), (68, 1), (71, 3)]
    def section(t, ch, mel, oct=12, mv=0.32, arp=True, melody=True, countm=False):
        for ci, c in enumerate(ch):
            b0 = t + ci * bar; note(b0, c[0] + oct, 0.18, 2.0)
            if arp:
                for k, m in enumerate(c[1:]): note(b0 + beat * k + beat * 0.5, m + oct, 0.10)
        if melody:
            tm = t
            for m, d in mel:
                if m: note(tm, m + oct, mv)
                if m and countm: note(tm + beat * 0.5, m + oct + 12, 0.07, 1.0)
                tm += d * beat
        return t + len(ch) * bar
    t = 0.0
    t = section(t, A_CH[:4], [], melody=False)
    t = section(t, A_CH, A_MEL); t = section(t, A_CH, A_MEL, countm=True)
    t = section(t, B_CH, B_MEL); t = section(t, B_CH, B_MEL, countm=True)
    brk = t; t = section(t, A_CH[:4], [], arp=False, melody=False)
    for k in range(8): note(brk + k * beat * 1.5, [88, 87, 88, 84, 83, 80, 81, 76][k], 0.09, 2.5)
    t = section(t, A_CH, A_MEL); t = section(t, A_CH, A_MEL, oct=24, mv=0.22)
    t = section(t, B_CH, B_MEL, countm=True); t = section(t, A_CH, A_MEL, countm=True); t = section(t, A_CH, A_MEL)
    end_music = t
    note(t, 69, 0.25, 4); note(t, 72, 0.15, 4); note(t, 76, 0.15, 4); note(t + beat, 81, 0.2, 4)
    tt = np.arange(N) / sr
    drone = 0.05 * np.sin(2 * np.pi * 55 * tt) + 0.035 * np.sin(2 * np.pi * 58.27 * tt) + 0.02 * np.sin(2 * np.pi * 110.3 * tt)
    drone *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * tt)) * np.clip(tt / 6, 0, 1)
    drone *= (1 + 1.2 * np.exp(-((tt - (brk + 3)) / 2.5) ** 2))
    mix = out + drone.astype(np.float32)
    ir_n = int(2.4 * sr); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / sr * 2.6); ir[0] = 1
    wet = fftconvolve(mix, ir)[:N]; wet /= np.abs(wet).max()
    mix = 0.55 * mix / np.abs(mix).max() + 0.6 * wet
    w = np.ones(N); st = int((end_music - 3.5) * sr); w[st:] = np.maximum(0.45, np.linspace(1, 0.3, N - st))
    idx = np.minimum(np.cumsum(w) - 1, N - 1); mix = np.interp(idx, np.arange(N), mix)
    L = int(TOTAL * sr); mix = mix[:L]
    fade = np.ones(L); fade[-int(3 * sr):] = np.linspace(1, 0, int(3 * sr)) ** 1.5; mix *= fade
    mix = mix / np.abs(mix).max() * 0.89
    write(path, mix); return path

def bgm_for(total, out, track):
    sr, m = wavfile.read(track); m = m.astype(np.float32)
    if m.ndim > 1: m = m.mean(1)
    N = int(total * SR); xf = int(2.0 * SR)
    body = m[:len(m) - int(3.0 * SR)]          # drop the fade-out tail when looping
    res = np.zeros(0, np.float32)
    while len(res) < N:
        if len(res) == 0: res = body.copy()
        else:
            r = np.linspace(0, 1, xf, dtype=np.float32)
            res = np.r_[res[:-xf], res[-xf:] * (1 - r) + body[:xf] * r, body[xf:]]
    res = res[:N]
    fo = int(min(2.5, total / 4) * SR); res[-fo:] *= np.linspace(1, 0, fo)
    write(out, res); return out

def _lp(x, a):   # one-pole low-pass
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)

def sfx_for(total, heads, scares, out, photos=(), heart=None, thunder_at=(0.0,)):
    """sound effects track: whoosh + low hit on every item, camera shutter when a photo appears,
    heartbeat over `heart`=(start,end), thunder at start, boom after scares, quiet wind under everything"""
    from scipy.signal import lfilter
    rng = np.random.default_rng(3); N = int(total * SR); s = np.zeros(N)
    def put(t, x, g=1.0):
        i = int(t * SR)
        if i < 0: x = x[-i:]; i = 0
        n = min(len(x), N - i)
        if n > 0: s[i:i + n] += g * x[:n]
    def whoosh(d=0.45):
        n = int(d * SR); x = rng.standard_normal(n); tt = np.arange(n) / n
        env = np.sin(np.pi * tt) ** 2
        lo = _lp(x, 0.97); hi = x - _lp(x, 0.6)
        return (lo * (1 - tt) + hi * tt * 0.5) * env * 0.9
    def hit():
        n = int(0.6 * SR); tt = np.arange(n) / SR
        return (np.sin(2 * np.pi * (70 - 30 * tt) * tt) * np.exp(-tt * 7) + 0.25 * _lp(rng.standard_normal(n), 0.9) * np.exp(-tt * 18))
    def shutter():
        n = int(0.12 * SR); tt = np.arange(n) / SR; c = rng.standard_normal(n) * np.exp(-tt * 140)
        x = np.zeros(int(0.2 * SR)); x[:n] += c; x[int(0.07 * SR):int(0.07 * SR) + n] += 0.7 * c
        return x - _lp(x, 0.5)
    def beat():
        n = int(0.25 * SR); tt = np.arange(n) / SR
        return np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 22)
    def thunder():
        n = int(3.5 * SR); tt = np.arange(n) / SR
        x = _lp(rng.standard_normal(n), 0.995) * 25
        return x * (np.exp(-tt * 1.4) * (1 + 0.6 * np.sin(2 * np.pi * 3.1 * tt)) * np.clip(tt / 0.05, 0, 1))
    for t in thunder_at: put(t, thunder(), 0.55)
    for t in heads:
        put(t - 0.25, whoosh(), 0.35); put(t, hit(), 0.45)
        i = max(0, int((t - 0.12) * SR)); n = min(int(0.22 * SR), N - i)
        if n > 0: s[i:i + n] += 0.12 * rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 12)
    for t in photos: put(t + 0.05, shutter(), 0.5)
    if heart:
        t = heart[0]
        while t < heart[1]:
            put(t, beat(), 0.55); put(t + 0.24, beat(), 0.4); t += 0.9
    for t in scares:
        n = int(1.6 * SR); x = np.arange(n) / SR
        put(t + 0.05, 0.9 * np.sin(2 * np.pi * (48 - 18 * x) * x) * np.exp(-x * 2.5) + 0.3 * rng.standard_normal(n) * np.exp(-x * 20))
        sw = np.arange(int(0.9 * SR)) / SR
        put(t + 0.05, 0.12 * np.sin(2 * np.pi * (900 + 1400 * sw) * sw) * np.exp(-sw * 3) * (1 + 0.5 * np.sin(2 * np.pi * 31 * sw)))
    wind = _lp(rng.standard_normal(N), 0.995) * 6
    wind *= 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(N) / SR / 7.0) ** 2
    s += 0.05 * wind
    write(out, s * 0.9); return out

def mix(voice, bgm, sfx, out, bgm_vol=0.32):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', voice, '-i', bgm, '-i', sfx, '-filter_complex',
        f'[1]volume={bgm_vol}[b];[0]asplit[v][sc];[b][sc]sidechaincompress=threshold=0.05:ratio=4:release=300[bd];'
        '[v][bd][2]amix=inputs=3:normalize=0,alimiter=limit=0.95[o]', '-map', '[o]', '-ar', str(SR), out], check=True)
    return out
