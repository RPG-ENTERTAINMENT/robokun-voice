"""One-time migration (run by hatena/main.sh, then deleted): adds the indoor rooms
(home / bedroom / toilet / bath / school / train / kitchen), starts each episode's opening
in the episode's own first scene, and gives every episode scenes that match its topic."""
import json, os
E = 'hatena/engine'
def edit(p, pairs):
    s = open(p).read()
    for a, b in pairs:
        if b in s: continue                          # already applied
        assert a in s, (p, a[:60]); s = s.replace(a, b, 1)
    open(p, 'w').write(s)

edit(f'{E}/world.py', [
 ("            if pattern == 'window' and",
  "            if pattern == 'tile' and (x % 8 == 7 or y % 8 == 7): c = tuple(min(255, v + 25) if sum(c) < 600 else v - 30 for v in c)\n"
  "            if pattern == 'checker' and ((x // 8) + (y // 8)) % 2: c = tuple(v - 70 for v in c)\n"
  "            if pattern == 'window' and"),
 ("# ---------- PROPS ----------",
  "# ---------- INDOOR ROOMS (engine/rooms.py) ----------\nexec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms.py')).read())\n\n# ---------- PROPS ----------"),
])
edit(f'{E}/render_cut.py', [
 ("def night():\n    world_bg.inputs['Color'].default_value = (0.03",
  "def _night_out():\n    world_bg.inputs['Color'].default_value = (0.03"),
 ("""SETNAME = CUT.get('set', 'park'); C = SETS.get(SETNAME, SETS['park'])
if SETNAME == 'sunset': sunset()
if SETNAME == 'night': night()""",
  """# indoor rooms built by engine/rooms.py on the row y = -100: name -> (x, background colour, sun energy)
ROOMS = {'home': (0, (0.93, 0.88, 0.78), 0.6), 'bedroom': (100, (0.12, 0.13, 0.22), 0.0), 'toilet': (200, (0.9, 0.92, 0.93), 0.4),
         'bath': (300, (0.85, 0.9, 0.93), 0.4), 'school': (400, (0.93, 0.88, 0.78), 0.6), 'train': (500, (0.88, 0.87, 0.84), 0.6),
         'kitchen': (600, (0.93, 0.88, 0.78), 0.6)}
for _k, (_x, _bg, _e) in ROOMS.items(): SETS[_k] = Vector((_x, -100.6, 0))
SETNAME = CUT.get('set', 'park'); C = SETS.get(SETNAME, SETS['park'])
def night():   # inside a room "night" only dims the room instead of building the outdoor night sky
    if SETNAME in ROOMS:
        world_bg.inputs['Strength'].default_value = 0.2; sun.data.energy = 0.0
    else: _night_out()
if SETNAME == 'sunset': sunset()
if SETNAME == 'night': night()
if SETNAME in ROOMS:
    _x, _bg, _e = ROOMS[SETNAME]
    world_bg.inputs['Color'].default_value = _bg + (1,); world_bg.inputs['Strength'].default_value = 0.55 if SETNAME != 'bedroom' else 0.25
    sun.data.energy = _e"""),
])
edit(f'{E}/plan.py', [
 ("""    cuts = [{'t0': 0.0, 't1': round(I / 2, 3), 'shot': 'introA', 'set': 'park'},
            {'t0': round(I / 2, 3), 't1': I, 'shot': 'introB', 'set': 'park'}]
    sets = tm.get('sets') or ['office', 'park', 'sunset']""",
  """    sets = tm.get('sets') or ['office', 'park', 'sunset']
    first = (L[0].get('set') if L else None) or sets[0]   # the opening happens where the story starts
    cuts = [{'t0': 0.0, 't1': round(I / 2, 3), 'shot': 'introA', 'set': first},
            {'t0': round(I / 2, 3), 't1': I, 'shot': 'introB', 'set': first}]"""),
])

S = {1: ['home', 'bath', 'office'], 2: ['home', 'school'], 3: ['bedroom', 'sunset'], 4: ['bedroom', 'home'],
     5: ['office', 'train', 'home'], 6: ['bedroom', 'school'], 7: ['bedroom', 'home'], 8: ['bedroom', 'toilet', 'office'],
     9: ['train', 'school'], 10: ['toilet', 'school', 'bedroom'], 11: ['bedroom'], 12: ['bedroom', 'school'],
     13: ['office', 'school', 'home'], 14: ['train', 'home'], 15: ['school', 'office'], 16: ['bath', 'toilet', 'home'],
     17: ['train', 'home'], 18: ['kitchen', 'office'], 19: ['bedroom', 'home'], 20: ['home', 'park'], 21: ['home', 'park'],
     22: ['home', 'park'], 23: ['train', 'park'], 24: ['school', 'park'], 25: ['bedroom', 'school'], 26: ['night', 'school'],
     27: ['school', 'office'], 28: ['train', 'park']}
for n, sets in S.items():
    p = f'hatena/episodes/ep{n:03d}.json'
    if not os.path.exists(p): continue
    e = json.load(open(p)); L = e['lines']; e['sets'] = sets
    for i, l in enumerate(L):
        l['set'] = sets[min(len(sets) - 1, i * len(sets) // len(L))]
        if l.get('fx') == 'walkin' and l['set'] != 'office': l.pop('fx')
    open(p, 'w').write(json.dumps(e, ensure_ascii=False, separators=(',', ':')) + '\n')
print('MIGRATE SCENES OK')
