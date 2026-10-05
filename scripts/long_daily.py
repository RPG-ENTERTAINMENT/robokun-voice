"""Daily landscape episode: voice -> render -> thumbnail -> upload to YouTube, scheduled for 20:00 JST.
Runs after the 12:00 JST short is posted (cron 03:00 UTC). run from repo root inside the venv."""
import os, sys, json, glob, subprocess, datetime, math
TEST = '--test' in sys.argv; NOW = '--now' in sys.argv
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(datetime.timezone.utc); day = now.astimezone(JST).strftime('%Y%m%d')
eps = sorted(os.path.basename(p)[:-5] for p in glob.glob('episodes/long/l[0-9][0-9][0-9].json'))
st_path = 'state/long_state.json'; os.makedirs('state', exist_ok=True)
st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'days': {}}
if day in st['days'] and not TEST: print('already done today', st['days'][day]); sys.exit(0)
if not eps: print('no long episodes'); sys.exit(0)
idx = st['next'] % len(eps); epid = eps[idx]; no = idx + 1 + (len(eps) * (st['next'] // len(eps)))
print('long episode', epid, 'no', no, flush=True)
env = dict(os.environ, ROBO_ASSETS=os.path.abspath('assets') + '/', ROBO_ASPECT='16x9')
vo = f'vo/long/{epid}'
sh('python', 'scripts/robo_tts.py', f'long/{epid}')
sh('python', 'eng/tts_vv.py', f'episodes/long/{epid}.json', vo, '--vv', 'vv', '--skip-robo')
# pad the ending so the episode is at least 8:00 (engine info runs in a subprocess to keep memory low)
def info(path): return json.loads(subprocess.run(['python', 'scripts/long_info.py', path, vo], env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
ep = json.load(open(f'episodes/long/{epid}.json'))
T = info(f'episodes/long/{epid}.json')['T']
if T < 480:
    last = ep['beats'][-1]; last['dur'] = float(last.get('dur', 0)) + min(20, 480 - T + 0.5)
os.makedirs('out', exist_ok=True); epf = f'out/{epid}.json'; json.dump(ep, open(epf, 'w'), ensure_ascii=False)
inf = info(epf); print('length', round(inf['T'], 1), flush=True)
mp4, png = f'out/{epid}.mp4', f'out/{epid}.png'
sh('python', 'eng/engine_l.py', epf, vo, mp4, '--procs', os.environ.get('LONG_PROCS') or str(min(4, os.cpu_count() or 2)), env=env)
sh('python', 'scripts/thumb_long.py', epf, vo, png, str(no), env=env)
# ---- metadata
def mmss(t): t = int(t); return f'{t // 60}:{t % 60:02d}'
ch = ['0:00 プロローグ'] + [f"{mmss(c0)} {ct}" + (f"「{cs}」" if cs else '') for (c0, ct, cs) in inf['cards']]
yc = json.load(open('config/youtube.json'))
desc = (ep.get('summary', '').strip() + '\n\n' + '\n'.join(ch) + '\n\n' +
        '毎日20時に8分アニメ、12時と19時にショートを更新中。\n\n#ロボしず #アニメ #オリジナルアニメ #癒し\n\n' + yc.get('credits', ''))
meta = {'title': ep.get('yt_title') or f"{ep['title']}｜ロボしず【8分アニメ】", 'description': desc,
        'tags': ['ロボしず', 'アニメ', 'オリジナルアニメ', '癒し', '短編アニメ', ep['title'].replace(' ', '')],
        'privacy': 'public', 'made_for_kids': False, 'category': '1', 'min_dur': 420, 'max_dur': 620}
pub = now.astimezone(JST).replace(hour=20, minute=0, second=0, microsecond=0)
if not NOW and pub - now > datetime.timedelta(minutes=15):
    meta['publish_at'] = pub.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
mf = f'out/{epid}.yt.json'; json.dump(meta, open(mf, 'w'), ensure_ascii=False, indent=1)
if TEST:
    os.makedirs('tests', exist_ok=True); import shutil
    shutil.copy(png, 'tests/long_thumb.png'); shutil.copy(mf, 'tests/long_meta.json')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '60', '-t', '30', '-i', mp4, '-c', 'copy', 'tests/long_clip.mp4'])
    print('test done (not uploaded)'); sys.exit(0)
r = subprocess.run(['python', 'scripts/post_long.py', mp4, png, mf], capture_output=True, text=True); print(r.stdout, r.stderr[-2000:])
vid = next((l.split()[2] for l in r.stdout.splitlines() if l.startswith('youtube ok')), None)
if vid:
    st['days'][day] = {'ep': epid, 'video': vid}; st['next'] += 1
    json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1)
else: sys.exit('upload failed')
