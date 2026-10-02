"""Small edits applied to files from robokun_assets.zip (so the 23MB zip never needs re-uploading)."""
import re
P = [
 ('eng/engine.py', "def caption(C, text, prog, alpha, y=1640):", "def caption(C, text, prog, alpha, y=250):"),
 ('eng/engine.py', "'ロボしず', t, 360, a)", "'ロボしず', t, 600, a)"),
]
for f, a, b in P:
    s = open(f, encoding='utf-8').read()
    if a in s: s = s.replace(a, b); open(f, 'w', encoding='utf-8').write(s); print('patched', f, a[:40])
    elif b in s: print('already', f, b[:40])
    else: print('WARN pattern not found', f, a[:40])
