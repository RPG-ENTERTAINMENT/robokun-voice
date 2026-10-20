"""igc/render.py をそのまま使い、右上のスクール名だけ spec の brand に差し替えて実行する。"""
import os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'igc', 'render.py')
src = open(P, encoding='utf-8').read()
a = "t2 = 'RPGクリエイタースクール'"
assert a in src, 'render.py changed'
src = src.replace(a, "t2 = ep.get('brand', 'RPGクリエイタースクール')")
exec(compile(src, os.path.abspath(P), 'exec'), {'__file__': os.path.abspath(P), '__name__': '__main__'})
