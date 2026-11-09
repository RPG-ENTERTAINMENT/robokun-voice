"""Cut plan from timing.json: intro (2 cuts) + 1-2 cuts per line (3-5 s each) + ending.
  python plan.py <timing.json> <plan.json> <episode no>"""
import sys, json
GEN = {'ol': ['close', 'two', 'low', 'ots', 'side', 'close', 'crane'], 'robo': ['close', 'ots', 'two', 'low', 'side', 'close', 'crane']}
MAXCUT = 4.6

def make(tm, no):
    I, END, L = tm['intro'], tm['end'], tm['lines']
    cuts = [{'t0': 0.0, 't1': round(I / 2, 3), 'shot': 'introA', 'set': 'park'},
            {'t0': round(I / 2, 3), 't1': I, 'shot': 'introB', 'set': 'park'}]
    sets = tm.get('sets') or ['office', 'park', 'sunset']
    gi = {'ol': no % 3, 'robo': (no + 1) % 3}; prev = None
    def generic(sp):
        nonlocal prev
        for _ in range(7):
            s = GEN[sp][gi[sp] % len(GEN[sp])]; gi[sp] += 1
            if s != prev: return s
        return 'two'
    for i, ln in enumerate(L):
        t0 = I if i == 0 else round(ln['s'] - 0.12, 3)
        t1 = END if i == len(L) - 1 else round(L[i + 1]['s'] - 0.12, 3)
        st = ln.get('set') or sets[min(len(sets) - 1, i * len(sets) // len(L))]
        last = i == len(L) - 1
        base = {'sp': ln['sp'], 'set': st, 'who': ln.get('who', ln['sp']), 'line': i}
        for k in ('act_ol', 'act_robo', 'phone'):
            if k in ln: base[k] = ln[k]
        fx = ln.get('fx')
        if last: shots = ['endA', 'endB']
        else: shots = [fx or generic(ln['sp'])]
        n = 2 if (t1 - t0) > MAXCUT else 1
        if last: n = 2 if (t1 - t0) > 3.2 else 1
        if n == 2 and not last: shots.append(generic(ln['sp']))
        bounds = [t0, round((t0 + t1) / 2, 3), t1] if n == 2 else [t0, t1]
        for k in range(n):
            c = dict(base, t0=bounds[k], t1=bounds[k + 1], shot=shots[k])
            if k == 1: c.pop('act_ol', None); c.pop('act_robo', None)   # overrides belong to the line's first cut
            cuts.append(c); prev = shots[k]
    return {'no': no, 'cfps': 12, 'intro': I, 'end': END, 'cuts': cuts}

if __name__ == '__main__':
    tm = json.load(open(sys.argv[1]))
    p = make(tm, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    json.dump(p, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
    print('PLAN', len(p['cuts']), 'cuts', [c['shot'] for c in p['cuts']])
