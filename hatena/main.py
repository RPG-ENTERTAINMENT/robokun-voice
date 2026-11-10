"""あなたのハテナを解決してみる OLゆりとロボしず（YouTube @hatenayurirobo）— Blenderのブロック世界の雑学ショートを毎日1本（18:00 JST 予約公開）
  python hatena/main.py test [n]  -> 第n話を1本作って GitHub release「hatena-test」に置く（投稿しない）
  python hatena/main.py batch 2,3,4 -> 複数話を作って GitHub release「hatena-batch」に置く（投稿しない）
  python hatena/main.py daily     -> 今日の1本を作って予約投稿（hatena/PAUSED があれば何もしない）
リポジトリのルートで ~/hvenv/bin/python から実行（hatena/main.sh）。台本は hatena/episodes/epNNN.json。"""
import os, sys, json, subprocess, datetime, base64, hashlib, glob, time
D = 'hatena'; E = os.path.join(D, 'engine')
PY = sys.executable
JST = datetime.timezone(datetime.timedelta(hours=9))
SLOTS = [(18, 0)]
WORK = os.environ.setdefault('HATENA_WORK', '/tmp/hatena_work')
TAGS = ['雑学', '豆知識', 'ブロック雑学', 'マイクラ風', 'アニメ', 'ゆり', 'ロボしず', 'なぜ', 'shorts']
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)

def episodes(): return sorted(glob.glob(f'{D}/episodes/ep*.json'))
def ep_path(n):
    eps = episodes(); return eps[(n - 1) % len(eps)]

def assets():
    if os.path.exists(f'{WORK}/world.blend'): return
    os.makedirs(WORK, exist_ok=True)
    for s in ['build_hakota.py', 'build_chars.py', 'world.py']: sh(PY, f'{E}/{s}')

def build(n, out):
    t0 = time.time(); assets(); ep = json.load(open(ep_path(n)))
    wd = f'/tmp/hatena_ep{n:03d}'; os.makedirs(wd, exist_ok=True)
    if not os.path.exists(f'{wd}/timing.json'): sh(PY, f'{E}/tts.py', ep_path(n), wd)
    sh(PY, f'{E}/plan.py', f'{wd}/timing.json', f'{wd}/plan.json', str(n))
    cuts = json.load(open(f'{wd}/plan.json'))['cuts']
    procs = []; par = max(1, (os.cpu_count() or 2) // 2)
    for i in range(len(cuts)):
        while len([p for p in procs if p.poll() is None]) >= par: time.sleep(2)
        procs.append(subprocess.Popen([PY, f'{E}/render_cut.py', f'{wd}/plan.json', str(i), f'{wd}/frames'],
                                      stdout=open(f'{wd}/cut{i:02d}.log', 'w'), stderr=subprocess.STDOUT))
    for p in procs: p.wait()
    bad = [i for i, p in enumerate(procs) if p.returncode != 0]
    if bad:
        for i in bad: print(open(f'{wd}/cut{i:02d}.log').read()[-1500:])
        raise SystemExit(f'cuts failed: {bad}')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    sh(PY, f'{E}/compose.py', ep_path(n), f'{wd}/timing.json', f'{wd}/plan.json', f'{wd}/frames', f'{wd}/voice.wav', out)
    print('BUILD', n, round((time.time() - t0) / 60, 1), 'min', flush=True)
    return ep

def title(ep): return f"{ep['title'].replace(chr(10), '')} #雑学 #shorts"[:100]
def description(ep):
    return (f"{ep['title'].replace(chr(10), '')}\n\n{ep.get('summary', '')}\n\n"
            "OLのゆりと、苔むしたロボット「ロボしず」が、ブロックの世界で「え、なんで？」を解決するショート。毎日18時に更新中。\n"
            "みんなの「ハテナ」もコメントで教えてね！\n\n#雑学 #豆知識 #なぜ #ゆりとロボしず #shorts")

def youtube():
    from cryptography.fernet import Fernet
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as gbuild
    csec = os.environ['YT_CLIENT_SECRET']
    fk = Fernet(base64.urlsafe_b64encode(hashlib.sha256(csec.encode()).digest()))
    rt = fk.decrypt(open(f'{D}/rt.enc', 'rb').read()).decode()
    cr = Credentials(None, refresh_token=rt, token_uri='https://oauth2.googleapis.com/token', client_id=os.environ['YT_CLIENT_ID'],
                     client_secret=csec, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly'])
    yt = gbuild('youtube', 'v3', credentials=cr)
    mine = [c['id'] for c in yt.channels().list(part='id', mine=True).execute().get('items', [])]
    want = open(f'{D}/channel_id.txt').read().strip() if os.path.exists(f'{D}/channel_id.txt') else ''
    if not want or want not in mine: raise SystemExit(f'WRONG CHANNEL: token is for {mine}, expected {want}. Not uploading.')
    return yt

def send(yt, body, path):
    from googleapiclient.http import MediaFileUpload
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    return resp

def upload(yt, path, ep, when):
    status = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}
    now = datetime.datetime.now(datetime.timezone.utc)
    if when > now + datetime.timedelta(minutes=10): status['publishAt'] = when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else: status['privacyStatus'] = 'public'
    body = {'snippet': {'title': title(ep), 'description': description(ep)[:4900], 'tags': TAGS + ep.get('tags', []),
                        'categoryId': '27', 'defaultLanguage': 'ja'}, 'status': status}
    try:
        resp = send(yt, body, path)
    except Exception as e:
        print('upload retry with minimal metadata:', e, flush=True)
        body['snippet'] = {'title': title(ep), 'description': description(ep)[:4900], 'categoryId': '27'}
        resp = send(yt, body, path)
    print('uploaded', resp['id'], status, flush=True); return resp['id']

def daily():
    if os.path.exists(f'{D}/PAUSED'): print('hatena: auto-post PAUSED (delete hatena/PAUSED to resume) - skipping'); return
    if not os.path.exists(f'{D}/rt.enc'): print('YouTube not connected yet (hatena:auth_url / auth_code) - skipping'); return
    now = datetime.datetime.now(JST); day = (now + datetime.timedelta(hours=3)).date()
    st_path = f'{D}/state/state.json'; os.makedirs(f'{D}/state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 1, 'posted': {}}
    key = day.isoformat(); done = st['posted'].setdefault(key, {})
    for slot, (h, m) in enumerate(SLOTS):
        when = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
        if str(slot) in done: print('slot already posted', key, slot); continue
        if when < datetime.datetime.now(JST) - datetime.timedelta(hours=2): print('slot time passed, skip', key, slot); continue
        n = st['next']; path = f'{D}/out/hatena_{key}_{slot}.mp4'
        ep = build(n, path); vid = upload(youtube(), path, ep, when)
        done[str(slot)] = {'ep': n, 'file': os.path.basename(ep_path(n)), 'video': vid, 'at': when.isoformat()}; st['next'] = n + 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1); os.remove(path)

def test(n=None):
    st_path = f'{D}/state/state.json'
    n = int(n) if n else (json.load(open(st_path))['next'] if os.path.exists(st_path) else 1)
    out = f'{D}/out/hatena_test_{n:03d}.mp4'; build(n, out)
    subprocess.run(['gh', 'release', 'delete', 'hatena-test', '-y', '--cleanup-tag'])
    sh('gh', 'release', 'create', 'hatena-test', out, '--title', f'hatena test ep{n:03d}', '--notes', f'ep{n:03d}', '--prerelease')

def batch(ns):
    # build several episodes and put them all in GitHub release "hatena-batch" (no posting)
    ns = [int(x) for x in ns.split(',') if x.strip()]
    subprocess.run(['gh', 'release', 'delete', 'hatena-batch', '-y', '--cleanup-tag'])
    sh('gh', 'release', 'create', 'hatena-batch', '--title', 'hatena batch', '--notes', ','.join(f'ep{n:03d}' for n in ns), '--prerelease')
    for n in ns:
        out = f'{D}/out/hatena_ep{n:03d}.mp4'
        try:
            build(n, out); sh('gh', 'release', 'upload', 'hatena-batch', out, '--clobber')
        except BaseException as e: print('BATCH FAIL', n, e, flush=True)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'test'
    if cmd == 'daily': daily()
    elif cmd == 'batch': batch(sys.argv[2] if len(sys.argv) > 2 else '2,3,4')
    elif cmd == 'test': test(sys.argv[2] if len(sys.argv) > 2 else None)
