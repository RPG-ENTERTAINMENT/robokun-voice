"""忍者しずく チャレンジの台本を自動で作る。回の番号 n から毎回ちがうチャレンジを作る（同じ n なら同じ台本）。
使い方: python3 engine/gen.py 7 > episodes/ep007.json
"""
import json, random, sys

TYPES = ['target', 'slice', 'catch', 'magic', 'karaoke', 'moving']

INTRO = ["Hi! I'm Ninja Shizuku!\nI work at NINJA DIGITAL BAR!",
         "Hey everyone! Ninja Shizuku here!\nWelcome to NINJA DIGITAL BAR!",
         "Ninja Shizuku is back!\nLive from NINJA DIGITAL BAR!",
         "Hello from Tokyo!\nIt's me, Ninja Shizuku!"]
FAIL_REACT = ["Whaaat?!", "Nooo way!", "Hmm... not yet!", "That was a warm-up!", "Oops! One more time!"]
FOCUS = ["Focus... focus...", "Deep breath...", "Ninja eyes ON!", "I can do this!"]
CHARGE = ["Ninja power... CHARGE!", "Full power jutsu!", "Secret technique... GO!", "Let's finish this!"]
CLEAR = ["Challenge CLEAR!", "I did it!!", "Ninja level UP!", "Nailed it!"]
ELEM = ['fire', 'ice', 'thunder', 'love', 'magic']
TINT = {'fire': [255, 90, 30], 'ice': [60, 160, 255], 'thunder': [255, 230, 60], 'love': [255, 80, 170], 'magic': [170, 100, 255]}


def opening(r, no, q, pose='cheer'):
    return [
        {"dur": 2.2, "pose": pose, "motion": "bob", "title": {"no": f"CHALLENGE #{no}", "q": q}, "sfx": [[0.05, "ding"]],
         "fx": [{"type": "sparkle", "at": 0, "dur": 2.2, "kind": "magic"}]},
        {"dur": 2.5, "pose": "wave", "motion": "bob", "cap": r.choice(INTRO), "sfx": [[0.0, "pop"]]},
    ]


def ending(r):
    return [{"dur": 4.6, "pose": "glow", "motion": "bob", "target": False, "end": {"pose": "wave"}, "sfx": [[0.2, "pop"], [0.6, "sparkle"]]}]


def ep_target(r, n, moving=False):
    el = r.choice(ELEM)
    tgt = [r.choice([700, 760, 820]), r.choice([520, 560, 620])]
    q = r.choice(["MOVING\nTARGET!", "HIT THE\nMOVING TARGET!"]) if moving else r.choice(["SHURIKEN\nBULLSEYE!", "ONE SHOT\nBULLSEYE?", "HIT THE\nTARGET!"])
    sc = opening(r, n, q)
    sc.append({"dur": 2.6, "pose": "point", "motion": "bob", "cap": "Today's challenge:\n" + ("Hit the MOVING target!" if moving else "Hit the target with a shuriken!"),
               "sfx": [[0.0, "pop"], [0.4, "sparkle"]], "wall_boost": 0.3})
    tries = r.choice([2, 3])
    for i in range(1, tries):
        sc.append({"dur": 1.0, "pose": "stand1" if i == 1 else "think", "motion": "none", "big": f"TRY {i}", "big_col": [255, 255, 255],
                   "cap": r.choice(FOCUS) if i > 1 else None, "sfx": [[0.0, "drum"]]})
        sc.append({"dur": 1.8, "pose": "shuriken", "motion": "none",
                   "fx": [{"type": "throw", "at": 0.1, "dur": 0.6, "result": "miss", "miss_dx": r.choice([-260, 200, 240]), "miss_dy": r.choice([-200, -150, 120]), "kind": r.choice(ELEM)}],
                   "big": "MISS!" if i == 1 else "SO CLOSE!", "big_at": 0.85, "big_col": [120, 200, 255] if i == 1 else [255, 200, 70], "sfx": [[0.1, "whoosh"], [0.85, "oops"]]})
        sc.append({"dur": 1.3, "pose": "surprise", "motion": "shake", "cap": r.choice(FAIL_REACT), "sfx": [[0.0, "boing"]]})
    sc.append({"dur": 1.7, "pose": "wind", "motion": "bounce", "cap": r.choice(CHARGE), "fx": [{"type": "swirl", "at": 0, "dur": 1.7, "kind": el}],
               "sfx": [[0.0, "charge"]], "wall_boost": 0.5, "tint": TINT[el]})
    sc.append({"dur": 2.2, "pose": "shuriken", "motion": "none", "big": "PERFECT!!", "big_at": 0.75, "big_col": [255, 61, 139],
               "fx": [{"type": "throw", "at": 0.05, "dur": 0.6, "result": "hit", "kind": el}],
               "sfx": [[0.05, "whoosh"], [0.65, "boom"], [0.8, "ding"]], "tint": TINT[el]})
    sc.append({"dur": 2.4, "pose": "party", "motion": "jump", "cap": r.choice(CLEAR), "fx": [{"type": "confetti", "at": 0}], "sfx": [[0.0, "fanfare"]]})
    return {"target": tgt, "target_move": 170 if moving else 0, "scenes": sc + ending(r)}


def ep_slice(r, n):
    kinds = ['watermelon', 'apple', 'orange', 'grape']
    k = r.choice([3, 4, 5])
    q = r.choice([f"SLICE {k}\nFRUITS!", f"{k} FRUITS\nONE SLASH!"])
    sc = opening(r, n, q, pose='sword')
    sc.append({"dur": 2.6, "pose": "point", "motion": "bob", "cap": f"Today's challenge:\nSlice {k} flying fruits with ONE slash!", "sfx": [[0.0, "pop"]], "target": False})

    def throw(cnt, miss):
        items = []
        for j in range(cnt):
            x0 = r.choice([120, 960])
            items.append({"kind": r.choice(kinds), "t0": 0.1 + j * 0.12, "x0": x0, "x1": 1080 - x0 + r.randint(-150, 150), "peak": r.randint(420, 700), "fly": 1.5})
        return {"type": "fruits", "items": items, "slash_at": 0.95, "miss": miss}
    sc.append({"dur": 1.0, "pose": "stand1", "motion": "none", "big": "TRY 1", "big_col": [255, 255, 255], "sfx": [[0.0, "drum"]], "target": False})
    sc.append({"dur": 2.0, "pose": "sword", "motion": "none", "target": False, "fx": [throw(k, [k - 1])],
               "big": "ONE ESCAPED!", "big_at": 1.25, "big_size": 120, "big_col": [120, 200, 255], "sfx": [[0.1, "whoosh"], [0.95, "slash"], [1.3, "oops"]]})
    sc.append({"dur": 1.3, "pose": "surprise", "motion": "shake", "cap": r.choice(FAIL_REACT), "sfx": [[0.0, "boing"]], "target": False})
    el = r.choice(['ice', 'thunder', 'magic'])
    sc.append({"dur": 1.7, "pose": "wind", "motion": "bounce", "cap": r.choice(CHARGE), "fx": [{"type": "swirl", "at": 0, "dur": 1.7, "kind": el}],
               "sfx": [[0.0, "charge"]], "wall_boost": 0.5, "tint": TINT[el], "target": False})
    sc.append({"dur": 2.2, "pose": "sword", "motion": "none", "target": False, "fx": [throw(k, [])], "big": "SLICE MASTER!", "big_at": 1.2, "big_size": 120,
               "big_col": [255, 61, 139], "sfx": [[0.1, "whoosh"], [0.95, "slash"], [1.0, "boom"], [1.2, "ding"]], "tint": TINT[el]})
    sc.append({"dur": 2.4, "pose": "party", "motion": "jump", "cap": r.choice(CLEAR), "fx": [{"type": "confetti", "at": 0}], "sfx": [[0.0, "fanfare"]], "target": False})
    return {"show_target": False, "scenes": sc + ending(r)}


def ep_catch(r, n):
    tot = r.choice([4, 5])
    q = r.choice([f"CATCH {tot}\nONIGIRI!", "ONIGIRI\nRAIN!"])
    sc = opening(r, n, q, pose='onigiri')
    sc.append({"dur": 2.6, "pose": "point", "motion": "bob", "cap": f"Today's challenge:\nCatch {tot} falling onigiri!", "sfx": [[0.0, "pop"]]})
    xs = [r.choice([260, 380, 540, 700, 820]) for _ in range(tot + 1)]
    cur, got = 540, 0
    miss_i = r.randint(1, tot - 1)
    for i, x in enumerate(xs):
        caught = i != miss_i
        to = x if caught else (x + (300 if x < 540 else -300))
        sc.append({"dur": 1.15, "pose": "run", "flip": to < cur, "x": [cur, to], "motion": "none",
                   "fx": [{"type": "drop", "at": 0.1, "fall": 0.85, "x": x, "caught": caught}],
                   "hud": f"ONIGIRI {got}/{tot}", "sfx": [[0.95, "pop" if caught else "oops"]]})
        cur = to
        if caught:
            got += 1
        else:
            sc.append({"dur": 1.1, "pose": "surprise", "x": cur, "motion": "shake", "cap": "Noooo! My onigiri!", "hud": f"ONIGIRI {got}/{tot}", "sfx": [[0.0, "boing"]]})
        if got >= tot:
            break
    sc.append({"dur": 1.8, "pose": "onigiri", "x": cur, "motion": "bounce", "hud": f"ONIGIRI {got}/{tot}", "big": "ALL CAUGHT!", "big_size": 130,
               "big_col": [255, 61, 139], "fx": [{"type": "sparkle", "at": 0, "dur": 1.8, "kind": "love"}], "sfx": [[0.0, "ding"], [0.3, "sparkle"]]})
    sc.append({"dur": 2.4, "pose": "party", "x": cur, "motion": "jump", "cap": "Yummy! " + r.choice(CLEAR), "fx": [{"type": "confetti", "at": 0}], "sfx": [[0.0, "fanfare"]]})
    return {"show_target": False, "scenes": sc + ending(r)}


def ep_magic(r, n):
    el = r.choice(['love', 'magic', 'fire'])
    q = r.choice(["MAGIC HAT\nTRICK!", "NINJA MAGIC\nSHOW!"])
    sc = opening(r, n, q, pose='magic')
    sc.append({"dur": 2.6, "pose": "point", "x": 330, "motion": "bob", "cap": "Today's challenge:\nA magic trick with this hat!", "fx": [{"type": "hat", "at": 9, "dur": 1}], "sfx": [[0.0, "pop"]]})
    sc.append({"dur": 2.0, "pose": "magic", "x": 330, "motion": "none", "cap": "Abracadabra...", "fx": [{"type": "hat", "at": 0.5, "dur": 1.0}], "sfx": [[0.0, "drum"], [1.3, "oops"]]})
    sc.append({"dur": 1.4, "pose": "surprise", "x": 330, "motion": "shake", "cap": "...nothing came out?!", "fx": [{"type": "hat", "at": 9, "dur": 1}], "sfx": [[0.0, "boing"]]})
    sc.append({"dur": 1.7, "pose": "wind", "x": 330, "motion": "bounce", "cap": r.choice(CHARGE), "fx": [{"type": "hat", "at": 9, "dur": 1}, {"type": "swirl", "at": 0, "dur": 1.7, "kind": el}],
               "sfx": [[0.0, "charge"]], "tint": TINT[el], "wall_boost": 0.4})
    sc.append({"dur": 2.4, "pose": "magic", "x": 330, "motion": "none", "big": "TA-DA!!", "big_at": 0.8, "big_col": [255, 61, 139],
               "fx": [{"type": "hat", "at": 0.1, "dur": 0.7, "pop": True, "kind": el}], "sfx": [[0.0, "drum"], [0.8, "boom"], [0.9, "sparkle"], [1.1, "fanfare"]], "tint": TINT[el]})
    sc.append({"dur": 2.3, "pose": "party", "x": 330, "motion": "jump", "cap": r.choice(CLEAR), "fx": [{"type": "hat", "at": 9, "dur": 1}], "sfx": [[0.0, "ding"]]})
    for s in sc:
        s.setdefault("target", False)
    return {"show_target": False, "scenes": sc + ending(r)}


def ep_karaoke(r, n):
    s1 = r.choice([58, 64, 71, 77])
    q = r.choice(["KARAOKE\n100 POINTS?", "PERFECT\nSCORE?"])
    sc = opening(r, n, q, pose='sing')
    sc.append({"dur": 2.6, "pose": "point", "motion": "bob", "cap": "Today's challenge:\nGet 100 points at karaoke!", "sfx": [[0.0, "pop"]]})
    sc.append({"dur": 2.4, "pose": "sing", "motion": "bob", "cap": "La la la~", "fx": [{"type": "notes", "at": 0, "dur": 2.4}], "sfx": [[0.0, "sparkle"]]})
    sc.append({"dur": 2.0, "pose": "sing", "motion": "none", "fx": [{"type": "meter", "at": 0.1, "dur": 1.2, "to": s1}], "sfx": [[0.0, "drum"], [1.3, "oops"]]})
    sc.append({"dur": 1.3, "pose": "surprise", "motion": "shake", "cap": f"Only {s1} points?!", "fx": [{"type": "meter", "at": 0, "dur": 0.01, "from": s1, "to": s1}], "sfx": [[0.0, "boing"]]})
    sc.append({"dur": 1.8, "pose": "music", "motion": "bob", "cap": "Practice time...", "fx": [{"type": "notes", "at": 0, "dur": 1.8}], "sfx": [[0.0, "sparkle"]]})
    sc.append({"dur": 2.4, "pose": "sing", "motion": "bounce", "cap": "One more time!", "fx": [{"type": "notes", "at": 0, "dur": 2.4}, {"type": "sparkle", "at": 0, "dur": 2.4, "kind": "love"}], "wall_boost": 0.4})
    sc.append({"dur": 2.3, "pose": "glow", "motion": "none", "big": "100 POINTS!!", "big_at": 1.4, "big_y": 1000, "big_size": 120, "big_col": [255, 61, 139],
               "fx": [{"type": "meter", "at": 0.1, "dur": 1.2, "to": 100}, {"type": "burst", "at": 1.35, "xy": [540, 600], "kind": "magic", "flash": True, "shake": True}],
               "sfx": [[0.0, "drum"], [1.35, "boom"], [1.45, "fanfare"]]})
    sc.append({"dur": 2.3, "pose": "party", "motion": "jump", "cap": r.choice(CLEAR), "fx": [{"type": "confetti", "at": 0}], "sfx": [[0.0, "ding"]]})
    for s in sc:
        s.setdefault("target", False)
    return {"show_target": False, "scenes": sc + ending(r)}


TITLE = {'target': 'Can Ninja Shizuku hit the target?', 'moving': 'Can Ninja Shizuku hit the moving target?', 'slice': 'Can Ninja Shizuku slice every fruit?',
         'catch': 'Can Ninja Shizuku catch all the onigiri?', 'magic': 'Ninja Shizuku tries a magic trick!', 'karaoke': 'Can Ninja Shizuku get 100 points at karaoke?'}


def make(n):
    r = random.Random(n * 7919)
    typ = TYPES[(n - 1) % len(TYPES)]
    if typ == 'target':
        ep = ep_target(r, n)
    elif typ == 'moving':
        ep = ep_target(r, n, moving=True)
    elif typ == 'slice':
        ep = ep_slice(r, n)
    elif typ == 'catch':
        ep = ep_catch(r, n)
    elif typ == 'magic':
        ep = ep_magic(r, n)
    else:
        ep = ep_karaoke(r, n)
    for s in ep['scenes']:
        if s.get('cap') is None:
            s.pop('cap', None)
    ep.update({"no": n, "type": typ, "seed": n, "title": TITLE[typ]})
    return ep


if __name__ == '__main__':
    print(json.dumps(make(int(sys.argv[1])), ensure_ascii=False))
