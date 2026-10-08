"""Shorts-only tweaks applied to eng/engine_l.py after patches/engine_l.diff (landscape output is unchanged).
- hook: frame 1 already shows the title + the first speech bubble (no fade-in from black)
- tempo: tighter gaps between lines, faster walking, shorter held beats
- loop: no 'おしまい' card / fade-out; the last 0.45s dissolves back into frame 1
"""
import sys
f = sys.argv[1] if len(sys.argv) > 1 else 'eng/engine_l.py'
P = [
 ("WALK_V, DASH_V = 190., 1300.\n",
  "WALK_V, DASH_V = 190., 1300.\nif not LAND: WALK_V = 300.\n"),
 ("        t = 0.6\n        s.beats = []",
  "        t = 0.6 if LAND else 0.0\n        s.beats = []"),
 ("                st = t0+a+(0.1 if a > 0 else 0.15)\n",
  "                st = t0+a+(0.1 if a > 0 else 0.15) if LAND else t0+a+(0.05 if (a > 0 or i > 0) else 0.12)\n"),
 ("te = max(te, st+dur+float(ep.get('gap', 0.35)))",
  "te = max(te, st+dur+float(ep.get('gap', 0.35 if LAND else 0.12)))"),
 ("            te = max(te, t0+float(b.get('dur', 0)))\n",
  "            te = max(te, t0+float(b.get('dur', 0))*(1.0 if LAND else 0.75))\n"),
 ("        s.T = t+2.4\n",
  "        s.T = t+2.4 if LAND else t+0.5\n"),
 ("s.sfx.append((s.T_end+0.2, 'sting_end', 0.7))",
  "LAND and s.sfx.append((s.T_end+0.2, 'sting_end', 0.7))"),
 ("            a = ss((t-0.2)/0.5)*(1-ss((t-2.4)/0.5)); big_text(O, s.ep.get('title', ''), s.ep.get('series', 'ロボしず'), t, 380 if LAND else 600, a)",
  "            a = ss((t-0.2)/0.5)*(1-ss((t-2.4)/0.5)) if LAND else 1-ss((t-2.0)/0.4)\n"
  "            big_text(O, s.ep.get('title', ''), s.ep.get('series', 'ロボしず'), t if LAND else t+0.6, 380 if LAND else 600, a)"),
 ("            if L['who'] == 'narr':\n                if -0.2 < v < d+0.4: caption(O, L['text'], min(1, max(0, v/(d*0.75))), ss((v+0.2)/0.3)*(1-ss((v-d)/0.4)))\n                continue\n            if 0 <= v < d+0.45:",
  "            first = (not LAND) and L is s.lines[0]\n"
  "            if L['who'] == 'narr':\n"
  "                if first and v < d: caption(O, L['text'], 1, 1)\n"
  "                elif -0.2 < v < d+0.4: caption(O, L['text'], min(1, max(0, v/(d*0.75))), ss((v+0.2)/0.3)*(1-ss((v-d)/0.4)))\n"
  "                continue\n"
  "            if (-1 if first else 0) <= v < d+0.45:"),
 ("bubble(Ob, L['text'], min(1, v/max(0.3, d*0.7)), anchor, tip, v)",
  "bubble(Ob, L['text'], 1 if first else min(1, v/max(0.3, d*0.7)), anchor, tip, max(v, 0)+1 if first else v)"),
 ("        if t > s.T_end+0.1:\n            v = t-s.T_end-0.1; big_text(O, 'おしまい'",
  "        if LAND and t > s.T_end+0.1:\n            v = t-s.T_end-0.1; big_text(O, 'おしまい'"),
 ("        if fo > 0: out = out*(1-fo)",
  "        if fo > 0 and LAND: out = out*(1-fo)"),
 ("        fi = 1-ss(t/0.35)\n        if fi > 0: out = out*(1-fi)\n",
  "        fi = 1-ss(t/0.35)\n        if fi > 0 and LAND: out = out*(1-fi)\n"
  "        if not LAND and t > s.T-0.45 and not getattr(s, '_in0', False):\n"
  "            if not hasattr(s, '_f0'):\n"
  "                s._in0 = True; s._f0 = s.render(0.0).astype(np.float32)/255; s._in0 = False\n"
  "            k = ss((t-(s.T-0.45))/0.45); out = out*(1-k)+s._f0*k\n"),
 ("cues = s.music+[(s.T_end+0.1, None)]",
  "cues = s.music+[(s.T_end+0.1 if LAND else s.T+1, None)]"),
]
s = open(f, encoding='utf-8').read(); bad = 0
for a, b in P:
    if b in s: print('already', a[:50].strip()); continue
    n = s.count(a)
    if n != 1: print('WARN pattern found', n, 'times:', a[:60].strip()); bad += 1; continue
    s = s.replace(a, b)
open(f, 'w', encoding='utf-8').write(s)
print('shorts_tempo applied' if not bad else f'shorts_tempo: {bad} patterns missing')
