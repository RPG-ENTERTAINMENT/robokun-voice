"""Nightly: render the next 2 episodes and attach them to a GitHub release named day-YYYYMMDD (JST, the posting day)."""
import os, sys, json, subprocess, datetime, glob
TEST = '--test' in sys.argv
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)
day = (now + datetime.timedelta(hours=12)).strftime('%Y%m%d')   # run at 01:00 JST -> same day; manual runs in the evening -> next day
idx = json.load(open('episodes/index.json'))
st_path = 'state/state.json'; os.makedirs('state', exist_ok=True)
st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'days': {}}
n = 1 if TEST else 2
eps = [idx[(st['next']+k) % len(idx)]['id'] for k in range(n)]
print('episodes', eps)
env = dict(os.environ, ROBO_ASSETS=os.path.abspath('assets')+'/')
sh('python', 'scripts/robo_tts.py', *eps)
outs = []
for k, e in enumerate(eps):
    sh('python', 'eng/tts_vv.py', f'episodes/{e}.json', f'vo/{e}', '--vv', 'vv', '--skip-robo')
    out = f'out/{day}_{"AB"[k]}_{e}.mp4'; os.makedirs('out', exist_ok=True)
    sh('python', 'eng/engine.py', f'episodes/{e}.json', f'vo/{e}', out, '--procs', '2', env=env)
    outs.append(out)
if TEST:
    import shutil; os.makedirs('tests', exist_ok=True); shutil.copy(outs[0], 'tests/latest.mp4')
    sh('gh', 'release', 'create', f'test-{now.strftime("%Y%m%d%H%M")}', *outs, '--title', 'test render', '--notes', ' '.join(eps), '--prerelease')
    sys.exit()
tag = f'day-{day}'
subprocess.run(['gh', 'release', 'delete', tag, '-y', '--cleanup-tag'])
meta = {'A': eps[0], 'B': eps[1]}
open('out/meta.json', 'w').write(json.dumps(meta))
sh('gh', 'release', 'create', tag, *outs, 'out/meta.json', '--title', tag, '--notes', ' / '.join(eps))
st['next'] = (st['next']+n) % len(idx); st['days'][day] = meta
json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1)
# cleanup releases older than 14 days
r = subprocess.run(['gh', 'release', 'list', '--limit', '100', '--json', 'tagName'], capture_output=True, text=True)
for t in json.loads(r.stdout or '[]'):
    tg = t['tagName']
    if tg.startswith('day-') and tg[4:] < (now-datetime.timedelta(days=14)).strftime('%Y%m%d'):
        subprocess.run(['gh', 'release', 'delete', tg, '-y', '--cleanup-tag'])
