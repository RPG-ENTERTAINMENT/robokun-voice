import numpy as np, wave, json, os, sys, importlib
from scipy import signal
EPN = os.environ.get('EP', 'ep_engine')
EP = importlib.import_module(EPN)
globals().update({k: v for k, v in vars(EP).items() if not k.startswith('_')})
VOICE_DIR = getattr(EP, 'VOICE_DIR', 'voice')
BG_ = getattr(EP, 'BGM', {})

SR = 48000
N = int(DUR * SR)
rng = np.random.default_rng(3)
def T(t): return int(t * SR)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def env_ad(n, a=0.005, d=0.5):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1) * np.exp(-t / d)
    return e
def add(buf, x, t, g=1.0):
    i = T(t)
    if i >= len(buf): return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[:j - i] * g

# ---------------- BGM ----------------
bgm = np.zeros(N)
BPM = BG_.get('bpm', 100); beat = 60 / BPM; bar = beat * 4; TR = BG_.get('transpose', 0)
CH = {'C': [48, 52, 55, 60, 64], 'Am': [45, 52, 57, 60, 64], 'F': [41, 53, 57, 60, 65], 'G': [43, 50, 55, 59, 62], 'Em': [40, 52, 55, 59, 64]}
PROG = ['C', 'Am', 'F', 'G']
MEL0 = [[76, None, 79, None, 81, 79, 76, None], [72, None, 76, None, 74, 72, 69, None],
       [69, 72, 77, None, 76, 74, 72, None], [74, None, 71, 74, 79, None, None, None],
       [76, 79, 84, None, 83, 81, 79, None], [81, None, 79, 76, 72, None, 74, None],
       [77, 76, 74, 72, 74, None, 76, None], [74, None, None, None, 71, None, 74, None]]
MEL = BG_.get('mel', MEL0); PROG = BG_.get('prog', PROG)

def pluck(f, dur=1.2, bright=0.5):
    n = int(dur * SR); p = int(SR / f)
    buf = rng.uniform(-1, 1, p)
    buf = np.convolve(buf, [bright, 1 - bright], 'same')
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out
_PC = {}
def pl(m, dur=1.0):
    k = (m, dur)
    if k not in _PC: _PC[k] = pluck(mtof(m), dur)
    return _PC[k]
def glock(m, dur=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12)
    return x * env_ad(n, 0.002, 0.45)
def bass(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)
    return x * np.minimum(t / 0.01, 1) * np.exp(-t / 0.6)
def noise_hit(dur, lo, hi, dec):
    n = int(dur * SR); x = rng.standard_normal(n)
    b, a = signal.butter(2, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], 'band'); x = signal.lfilter(b, a, x)
    return x * np.exp(-np.arange(n) / SR / dec)

def section(t):
    for s0, s1, k, ch in SCENES:
        if s0 <= t < s1: return k
    return 'sun'

nbars = int(DUR / bar)
for bi in range(nbars):
    t0 = bi * bar
    sec = section(t0 + 0.1)
    last = bi == nbars - 1
    chn = 'C' if last else PROG[bi % 4]
    notes = [m + TR for m in CH[chn]]
    # ukulele strum: D . D U . U D U
    pat = [0, 1, 1.5, 2.5, 3, 3.5] if not last else [0]
    for k, p in enumerate(pat):
        for j, m in enumerate(notes[1:] if k % 2 == 0 else notes[1:][::-1]):
            add(bgm, pl(m + 12, 1.2), t0 + p * beat + j * 0.012, 0.16 * (1.0 if k == 0 else 0.7) * (0.7 if sec == 'rain' else 1))
    # bass
    add(bgm, bass(notes[0], bar * 0.48), t0, 0.35)
    if not last: add(bgm, bass(notes[0] + 7, bar * 0.48), t0 + 2 * beat, 0.25)
    # melody (music box)
    if bi >= 1 and not last:
        mel = MEL[(bi - 1) % 8]
        gv = 0.22 if sec != 'rain' else 0.15
        for s, m in enumerate(mel):
            if m: add(bgm, glock(m + TR, 1.0), t0 + s * beat / 2, gv)
    if last:
        for j, m in enumerate([72, 76, 79, 84]): add(bgm, glock(m + TR, 2.4), t0 + j * 0.06, 0.25)
    # shaker / claps (not in rain/snow quiet parts)
    if sec == 'sun' and not last:
        for s in range(8):
            add(bgm, noise_hit(0.08, 6000, 14000, 0.02), t0 + s * beat / 2, 0.05 if s % 2 else 0.08)
        for s in (1, 3):
            add(bgm, noise_hit(0.15, 900, 3000, 0.04), t0 + s * beat, 0.10)
    if sec in ('snow', 'night'):  # sleigh bells
        for s in range(8):
            add(bgm, noise_hit(0.12, 7000, 15000, 0.05) * np.sin(np.arange(int(0.12 * SR)) / SR * 2 * np.pi * 30) ** 2, t0 + s * beat / 2, 0.06)

# ---------------- voice ----------------
vo = np.zeros(N)
META = json.load(open(f'{VOICE_DIR}/meta.json'))
for k, t0 in VO.items():
    w = wave.open(f'{VOICE_DIR}/{k}.wav'); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
    if sr != SR: x = signal.resample_poly(x, SR, sr)
    # gentle presence + warmth
    b, a = signal.butter(2, 120 / (SR / 2), 'high'); x = signal.lfilter(b, a, x)
    add(vo, x, t0, 0.95)
# clarity EQ (no reverb): cut mud, add presence & air, light compression
def peq(x, f0, gdb, q):
    A = 10 ** (gdb / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(b, a, x)
def shelf_hi(x, f0, gdb):
    A = 10 ** (gdb / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w); sA = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
    a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    return signal.lfilter(b, a, x)
vo = peq(vo, 300, -3.5, 0.9)
vo = peq(vo, 3200, 4.0, 1.0)
vo = shelf_hi(vo, 7500, 3.0)
lvl = np.sqrt(np.convolve(vo ** 2, np.ones(480) / 480, 'same')) + 1e-6
gain = np.minimum(1, (0.12 / lvl) ** 0.4)
gain = np.convolve(gain, np.ones(240) / 240, 'same')
vo = vo * gain
vo = vo / np.abs(vo).max() * 0.95

# ducking envelope for BGM
env = np.abs(vo); win = int(0.05 * SR)
env = np.convolve(env, np.ones(win) / win, 'same')
duck = 1 - 0.7 * np.clip(env / 0.04, 0, 1)
duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), 'same')

# ---------------- SFX ----------------
sfx = np.zeros(N)
def pop(f0=600, f1=1400, dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / dur) ** 0.5
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04)
def whoosh(dur=0.6):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n)
    t = np.arange(n) / SR
    for i in range(0, n, 2400):
        fc = 400 + 4000 * np.sin(np.pi * i / n)
        b, a = signal.butter(2, [fc * 0.7 / (SR / 2), min(fc * 1.4, SR / 2 - 100) / (SR / 2)], 'band')
        out[i:i + 2400] = signal.lfilter(b, a, x[i:i + 2400])
    return out * np.sin(np.pi * t / dur) ** 2
def sparkle():
    out = np.zeros(int(1.2 * SR))
    for j, m in enumerate([84, 88, 91, 96, 100]):
        g = glock(m, 0.8); out[int(j * 0.05 * SR):int(j * 0.05 * SR) + len(g)] += g * 0.6
    return out
def step(p=1.0):
    n = int(0.09 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 140 * p * t) * 0.8 + noise_hit(0.09, 300, 1800, 0.015)) * np.exp(-t / 0.025)
def munch():
    return noise_hit(0.09, 600, 3500, 0.025) + 0.5 * noise_hit(0.09, 150, 500, 0.03)
def slurp(dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); out = np.zeros(n)
    for i in range(0, n, 1200):
        fc = 700 + 1600 * (i / n)
        b, a = signal.butter(2, [fc * 0.8 / (SR / 2), fc * 1.25 / (SR / 2)], 'band')
        out[i:i + 1200] = signal.lfilter(b, a, x[i:i + 1200])
    return out * np.sin(np.pi * t / dur) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t))
def bird():
    out = np.zeros(int(0.5 * SR))
    for j in range(2):
        n = int(0.09 * SR); t = np.arange(n) / SR
        f = 3800 + 1800 * np.sin(np.pi * t / 0.09) - 1500 * t / 0.09
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.09)
        out[int(j * 0.14 * SR):int(j * 0.14 * SR) + n] += c
    return out
def boing(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 260 + 180 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 120 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)
def rumble(dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    x = signal.sawtooth(2 * np.pi * (38 + 8 * np.sin(2 * np.pi * 7 * t)) * t) * 0.5 + noise_hit(dur, 60, 300, 1.0) * 0.5
    b, a = signal.butter(3, 500 / (SR / 2)); x = signal.lfilter(b, a, x)
    return x * np.minimum(t / 0.05, 1) * np.exp(-t / 0.5)
def blow(dur=0.35):
    return noise_hit(dur, 400, 2500, 1.0) * np.sin(np.pi * np.arange(int(dur * SR)) / SR / dur)

# rain ambience
def amb(t0, t1, kind):
    n = T(t1) - T(t0); x = rng.standard_normal(n)
    if kind == 'rain':
        b, a = signal.butter(2, [800 / (SR / 2), 7000 / (SR / 2)], 'band'); x = signal.lfilter(b, a, x) * 0.5
        drops = np.zeros(n); idx = rng.integers(0, n - 400, int((t1 - t0) * 30))
        for i in idx: drops[i:i + 300] += np.sin(np.arange(300) * rng.uniform(0.2, 0.5)) * np.exp(-np.arange(300) / 60) * rng.uniform(0.3, 1)
        x = x + drops * 0.6
    elif kind == 'crickets':
        x = np.zeros(n); tt0 = 0.0
        while tt0 < (t1 - t0) - 0.5:
            i = int(tt0 * SR); m = int(0.18 * SR); tt = np.arange(m) / SR
            f = rng.uniform(4200, 4800)
            x[i:i + m] += np.sin(2 * np.pi * f * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 38 * tt)) * np.sin(np.pi * tt / 0.18)
            tt0 += rng.uniform(0.35, 0.9)
    elif kind == 'boil':
        x = np.zeros(n); idx = rng.integers(0, n - 3000, int((t1 - t0) * 14))
        for i in idx:
            m = int(rng.uniform(600, 2400)); tt = np.arange(m) / SR; f = rng.uniform(140, 420) * (1 + 1.5 * tt / (m / SR))
            x[i:i + m] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.arange(m) / m) * rng.uniform(0.3, 1)
    else:
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * np.arange(n) / SR)
        b, a = signal.butter(2, [200 / (SR / 2), 1200 / (SR / 2)], 'band'); x = signal.lfilter(b, a, x) * lfo
    fade = np.minimum(1, np.minimum(np.arange(n) / SR / 0.8, (n - np.arange(n)) / SR / 0.6))
    return x * fade
if hasattr(EP, 'sfx_events'):
    EP.sfx_events(sys.modules[__name__])
else:
    raise SystemExit('episode module needs sfx_events')

# ---------------- mix ----------------
b, a = signal.butter(2, 3500 / (SR / 2))
bgm_l = bgm.copy()
rs = np.zeros(N, bool)
for s0, s1, k, ch in SCENES:
    if k == 'rain': rs[T(s0):T(s1)] = True
bgm_l[rs] = signal.lfilter(b, a, bgm)[rs]  # muffled BGM in rain
bgm_l = bgm_l / np.abs(bgm_l).max() * 0.26 * duck
for m0, m1 in getattr(EP, 'BGM_MUTE', []):
    g = np.ones(N); i0, i1 = T(m0), T(m1); fl = int(0.4 * SR)
    g[i0:i1] = 0; g[max(0, i0 - fl):i0] = np.linspace(1, 0, i0 - max(0, i0 - fl)); g[i1:i1 + fl] = np.linspace(0, 1, len(g[i1:i1 + fl]))
    bgm_l *= g
fin = np.ones(N); fo = T(max(0.0, DUR - 1.0)); fin[fo:] = np.linspace(1, 0.0, N - fo) ** 0.5
mix = (vo * 1.0 + bgm_l + sfx * 0.9) * fin
# stereo: slight width for bgm/sfx
L = mix + 0.03 * np.roll(bgm_l, 300); R = mix + 0.03 * np.roll(bgm_l, -300)
st = np.stack([L, R], 1)
st = np.tanh(st * 1.15 / np.abs(st).max() * 1.1) * 0.89
y = (st * 32767).astype(np.int16)
w = wave.open(os.environ.get('AIKA_AUDIO_OUT', 'out/audio.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes()); w.close()
print('ok', np.abs(st).max())
