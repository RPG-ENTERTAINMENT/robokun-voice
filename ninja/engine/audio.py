"""BGM（かわいいチップチューン風）と効果音をその場で作って混ぜる。外部の音源は使わない（著作権の心配なし）。"""
import numpy as np, wave, random, math

SR = 44100


def tone(f, dur, kind='sq', vol=0.3, att=0.005, rel=0.08):
    n = int(SR * dur)
    t = np.arange(n) / SR
    if kind == 'sq':
        w = np.sign(np.sin(2 * np.pi * f * t)) * 0.6
    elif kind == 'tri':
        w = 2 * np.abs(2 * (t * f % 1) - 1) - 1
    else:
        w = np.sin(2 * np.pi * f * t)
    env = np.ones(n)
    a = min(n, max(1, int(att * SR))); r = min(n, max(1, int(rel * SR)))
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.linspace(1, 0, r)
    return w * env * vol


def note_f(n):
    return 440 * 2 ** ((n - 69) / 12)


def bgm(total, seed=1, style='cute'):
    rnd = random.Random(seed)
    bpm = 128
    beat = 60 / bpm
    out = np.zeros(int(SR * (total + 1)))
    keys = [60, 62, 65, 67]  # C D F G
    key = rnd.choice(keys)
    prog = rnd.choice([[0, 7, 9, 5], [0, 5, 7, 0], [9, 5, 0, 7], [0, 9, 5, 7]])
    penta = [0, 2, 4, 7, 9, 12, 14, 16]
    motif = [rnd.choice(penta) for _ in range(8)]
    bar = beat * 4
    nbars = int(total / bar) + 2
    for b in range(nbars):
        root = key - 12 + prog[b % 4]
        t0 = b * bar
        # ベース（8分）
        for i in range(8):
            f = note_f(root + (12 if i % 2 else 0))
            s = tone(f, beat / 2 * 0.9, 'tri', 0.18, rel=0.03)
            st = int((t0 + i * beat / 2) * SR)
            out[st:st + len(s)] += s[:max(0, len(out) - st)]
        # 和音（裏拍のキラキラ）
        chord = [root + 12, root + 16 if prog[b % 4] in (0, 5, 7) else root + 15, root + 19]
        for i in (1, 3):
            for c in chord:
                s = tone(note_f(c + 12), beat * 0.35, 'sq', 0.035, rel=0.1)
                st = int((t0 + i * beat) * SR)
                out[st:st + len(s)] += s[:max(0, len(out) - st)]
        # メロディ
        mel = motif if b % 2 == 0 else [m + rnd.choice([0, 0, 2, -2]) for m in motif]
        for i, m in enumerate(mel):
            if rnd.random() < 0.18:
                continue
            f = note_f(key + 12 + m + (prog[b % 4] if prog[b % 4] < 7 else 0) % 12 * 0)
            s = tone(f, beat / 2 * 0.85, 'sq', 0.07, rel=0.05)
            st = int((t0 + i * beat / 2) * SR)
            out[st:st + len(s)] += s[:max(0, len(out) - st)]
        # ドラム
        for i in range(4):
            st = int((t0 + i * beat) * SR)
            k = kick()
            out[st:st + len(k)] += k[:max(0, len(out) - st)] * (1 if i % 2 == 0 else 0.5)
            hh = hat()
            st2 = int((t0 + i * beat + beat / 2) * SR)
            out[st2:st2 + len(hh)] += hh[:max(0, len(out) - st2)]
    n = int(SR * total)
    out = out[:n]
    fade = int(SR * 0.6)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out * 0.8


def kick():
    t = np.arange(int(SR * 0.18)) / SR
    f = 120 * np.exp(-t * 25) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * 0.35


def hat():
    t = np.arange(int(SR * 0.05)) / SR
    n = np.random.default_rng(3).uniform(-1, 1, len(t))
    n = np.diff(n, prepend=0)
    return n * np.exp(-t * 80) * 0.06


def sfx(name):
    rng = np.random.default_rng(abs(hash(name)) % 1000)
    if name == 'pop':
        t = np.arange(int(SR * 0.12)) / SR
        f = 900 * np.exp(-t * 30) + 300
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.5
    if name == 'ding':
        t = np.arange(int(SR * 0.7)) / SR
        return (np.sin(2 * np.pi * 1568 * t) + 0.5 * np.sin(2 * np.pi * 2349 * t)) * np.exp(-t * 6) * 0.3
    if name == 'whoosh':
        t = np.arange(int(SR * 0.4)) / SR
        n = rng.uniform(-1, 1, len(t))
        env = np.sin(np.pi * t / t[-1]) ** 2
        # 簡単なバンドパス（移動平均の差）
        sm = np.convolve(n, np.ones(8) / 8, 'same') - np.convolve(n, np.ones(40) / 40, 'same')
        return sm * env * 1.6
    if name == 'oops':
        t = np.arange(int(SR * 0.6)) / SR
        f = 700 * np.exp(-t * 2.5)
        w = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5
        return w * np.exp(-t * 3) * 0.25
    if name == 'boom':
        t = np.arange(int(SR * 1.0)) / SR
        n = rng.uniform(-1, 1, len(t))
        low = np.convolve(n, np.ones(60) / 60, 'same')
        f = 90 * np.exp(-t * 4) + 35
        return (low * 4 + np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 4) * 0.6
    if name == 'sparkle':
        out = np.zeros(int(SR * 0.8))
        for i, nn in enumerate([84, 88, 91, 96, 100]):
            s = tone(note_f(nn), 0.25, 'sin', 0.18, rel=0.2)
            st = int(i * 0.07 * SR)
            out[st:st + len(s)] += s
        return out
    if name == 'charge':
        t = np.arange(int(SR * 1.2)) / SR
        f = 200 + 900 * t / t[-1]
        return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.08 * (t / t[-1])
    if name == 'fanfare':
        out = np.zeros(int(SR * 1.4))
        for i, nn in enumerate([72, 76, 79, 84]):
            s = tone(note_f(nn), 0.5 if i == 3 else 0.14, 'sq', 0.12, rel=0.15)
            st = int(i * 0.13 * SR)
            out[st:st + len(s)] += s
        return out
    if name == 'drum':
        out = np.zeros(int(SR * 1.0))
        for i in range(14):
            st = int(i * 0.065 * SR)
            k = kick()[:int(SR * 0.06)] * (0.4 + i / 20)
            out[st:st + len(k)] += k
        return out
    if name == 'boing':
        t = np.arange(int(SR * 0.5)) / SR
        f = 220 + 200 * np.sin(t * 40) * np.exp(-t * 5)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.4
    if name == 'slash':
        t = np.arange(int(SR * 0.25)) / SR
        n = rng.uniform(-1, 1, len(t))
        return np.diff(n, prepend=0) * np.exp(-t * 14) * 0.4
    return np.zeros(10)


def mix(total, events, path, seed=1, bgm_style='cute', bgm=None):
    out = bgm_track = globals()['bgm'](total, seed)
    out = bgm_track.copy()
    for at, name in events:
        s = sfx(name)
        st = int(at * SR)
        if st >= len(out):
            continue
        e = min(len(out), st + len(s))
        out[st:e] += s[:e - st]
    out = np.tanh(out * 1.1) * 0.9
    data = (out * 32767).astype(np.int16)
    st = np.stack([data, data], 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(st.tobytes())
