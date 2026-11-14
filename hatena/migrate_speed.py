"""One-time migration (run by hatena/main.sh after migrate_scenes.py, then deleted):
only the room in use is rendered, so the extra rooms' lamps don't slow every frame down."""
p = 'hatena/engine/render_cut.py'; s = open(p).read()
a = """    sun.data.energy = _e
"""
b = """    sun.data.energy = _e
for _k in ROOMS:   # only the room in use is rendered (all rooms' lamps would otherwise slow every frame down)
    _c = bpy.data.collections.get(_k.capitalize())
    if _c and _k != SETNAME: _c.hide_render = True
"""
if b not in s:
    assert a in s, 'render_cut.py: ROOMS block not found'
    s = s.replace(a, b, 1); open(p, 'w').write(s)
print('MIGRATE SPEED OK')
