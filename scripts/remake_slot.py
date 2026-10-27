"""Replace today's slot (A or B) with the next episode in episodes/index.json and re-upload it to the day release.
Usage: remake_slot.py <A|B> [HH:MM]  -- HH:MM = TikTok post time used by the SNS admin (rpgtokyo.com/sns)."""
import os, sys, json, subprocess, datetime, glob
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)
slot = sys.argv[1]; at = sys.argv[2] if len(sys.argv) > 2 else ''
JST = datetime.timezone(datetime.timedelta(hours=9))
day = (datetime.datetime.now(JST) - datetime.timedelta(hours=6)).strftime('%Y%m%d')
tag = f'day-{day}'
idx = json.load(open('episodes/index.json'))
st = json.load(open('state/state.json'))
e = idx[st['next'] % len(idx)]['id']
print('remake', day, slot, '->', e)
sh('python', 'scripts/robo_tts.py', e)
sh('python', 'eng/tts_vv.py', f'episodes/{e}.json', f'vo/{e}', '--vv', 'vv', '--skip-robo')
for w in glob.glob(f'vo/{e}/[0-9][0-9].wav'):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-af', 'atempo=1.1', w+'.f.wav'], check=True); os.replace(w+'.f.wav', w)
os.makedirs('out', exist_ok=True); out = f'out/{day}_{slot}_{e}.mp4'
sh('python', 'eng/engine_l.py', f'episodes/{e}.json', f'vo/{e}', out, '--procs', '2', env=dict(os.environ, ROBO_ASSETS=os.path.abspath('assets')+'/'))
os.makedirs('dl', exist_ok=True)
sh('gh', 'release', 'download', tag, '-p', 'meta.json', '-D', 'dl', '--clobber')
meta = json.load(open('dl/meta.json'))
old = meta.get(slot)
meta[slot] = e
meta.setdefault('titles', {})[slot] = json.load(open(f'episodes/{e}.json')).get('title', '')
meta.setdefault('rev', {})[slot] = meta.get('rev', {}).get(slot, 1) + 1
if at: meta.setdefault('at', {})[slot] = at
open('out/meta.json', 'w').write(json.dumps(meta, ensure_ascii=False))
if old: subprocess.run(['gh', 'release', 'delete-asset', tag, f'{day}_{slot}_{old}.mp4', '-y'])
sh('gh', 'release', 'upload', tag, out, 'out/meta.json', '--clobber')
st['next'] = (st['next'] + 1) % len(idx)
st['days'].setdefault(day, {})[slot] = e
json.dump(st, open('state/state.json', 'w'), ensure_ascii=False, indent=1)
print('done', old, '->', e)
