"""OLあいかの車中泊ライフ — daily auto post.
  python main.py daily   -> make the day's 2 episodes and schedule them on YouTube (12:00 / 19:00 JST)
  python main.py smoke   -> environment check: voice + 3 s render of ep01, no upload
  python main.py render <epid>  -> render one episode to out/<epid>.mp4 (no upload)
Run from the aika/ directory."""
import os, sys, json, subprocess, datetime, glob, base64, hashlib, shutil
JST = datetime.timezone(datetime.timedelta(hours=9))
CHANNEL_ID = 'UCCA5tGpsDI7Nh1360ie3TqA'          # OLあいかの車中泊ライフ
SLOTS = [(12, 0), (19, 0)]
NPROC = os.cpu_count() or 2
def sh(*a, env=None):
    print('+', ' '.join(a), flush=True); subprocess.run(a, check=True, env=env)

def build(ep, seconds=None):
    spec, vdir = f'episodes/{ep}.json', f'voice/{ep}'
    sh(sys.executable, 'voice.py', spec, vdir)
    env = dict(os.environ, EP='ep_engine', AIKA_SPEC=spec, AIKA_VOICE=vdir, AIKA_AUDIO_OUT=f'out/{ep}.wav')
    os.makedirs('out', exist_ok=True)
    sh(sys.executable, 'audio.py', env=env)
    dur = json.loads(subprocess.run([sys.executable, '-c', 'import ep_engine as E, json; print(json.dumps(E.DUR))'],
                                    env=env, capture_output=True, text=True, check=True).stdout)
    nf = int(round((seconds or dur) * 30))
    # warm the prop cache once, then render in parallel chunks
    subprocess.run([sys.executable, '-c', 'import render'], env=env, check=True)
    cuts = [nf * i // NPROC for i in range(NPROC + 1)]
    procs = [subprocess.Popen([sys.executable, 'render.py', 'video', str(a), str(b), f'out/{ep}_p{i}.mp4'], env=env)
             for i, (a, b) in enumerate(zip(cuts, cuts[1:])) if b > a]
    for p in procs:
        if p.wait() != 0: raise SystemExit('render failed')
    with open(f'out/{ep}_list.txt', 'w') as f:
        for i in range(len(procs)): f.write(f"file '{ep}_p{i}.mp4'\n")
    sh('ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'out/{ep}_list.txt', '-i', f'out/{ep}.wav',
       '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-b:v', '3200k', '-maxrate', '3800k', '-bufsize', '7000k',
       '-pix_fmt', 'yuv420p', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
       '-movflags', '+faststart', '-shortest', f'out/{ep}.mp4')
    for p in glob.glob(f'out/{ep}_p*.mp4'): os.remove(p)
    return f'out/{ep}.mp4'

def youtube():
    from cryptography.fernet import Fernet
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as gbuild
    csec = os.environ['YT_CLIENT_SECRET']
    fk = Fernet(base64.urlsafe_b64encode(hashlib.sha256(csec.encode()).digest()))
    rt = fk.decrypt(open('rt.enc', 'rb').read()).decode()
    cr = Credentials(None, refresh_token=rt, token_uri='https://oauth2.googleapis.com/token', client_id=os.environ['YT_CLIENT_ID'],
                     client_secret=csec, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly'])
    yt = gbuild('youtube', 'v3', credentials=cr)
    mine = [c['id'] for c in yt.channels().list(part='id', mine=True).execute().get('items', [])]
    if CHANNEL_ID not in mine: raise SystemExit(f'WRONG CHANNEL: token is for {mine}, expected {CHANNEL_ID}. Not uploading.')
    return yt

def upload(yt, path, ep, when):
    from googleapiclient.http import MediaFileUpload
    spec = json.load(open(f'episodes/{ep}.json')); cfg = json.load(open('config.json'))
    title = f"{spec['title']}｜OLあいかの車中泊ライフ #shorts"[:100]
    status = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False}
    now = datetime.datetime.now(datetime.timezone.utc)
    if when > now + datetime.timedelta(minutes=10):
        status['publishAt'] = when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        status['privacyStatus'] = 'public'
    body = {'snippet': {'title': title, 'description': cfg['description'], 'tags': cfg['tags'], 'categoryId': cfg['category'],
                        'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    print('uploaded', ep, resp['id'], status, flush=True)
    return resp['id']

def daily():
    if not os.path.exists('rt.enc'): print('YouTube not connected yet (run auth_url / auth_code first) — skipping'); return
    now = datetime.datetime.now(JST)
    day = (now + datetime.timedelta(hours=4)).date()     # 20:00 or later -> prepare tomorrow
    st_path = 'state/state.json'; os.makedirs('state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'posted': {}}
    idx = json.load(open('episodes/index.json'))
    key = day.isoformat(); done = st['posted'].setdefault(key, {})
    yt = youtube()
    for slot, (h, m) in enumerate(SLOTS):
        if str(slot) in done: print('slot already posted', key, slot); continue
        if st['next'] >= len(idx): print('NO MORE EPISODES — add new ones to episodes/'); break
        ep = idx[st['next']]
        path = build(ep)
        when = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
        vid = upload(yt, path, ep, when)
        done[str(slot)] = {'ep': ep, 'video': vid, 'at': when.isoformat()}; st['next'] += 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1)
        shutil.rmtree(f'voice/{ep}', ignore_errors=True); os.remove(path)
    print('left in stock:', len(idx) - st['next'])

def now(n=2):
    # post n episodes immediately (public), continuing the stock order
    st_path = 'state/state.json'; os.makedirs('state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'posted': {}}
    idx = json.load(open('episodes/index.json'))
    yt = youtube()
    for _ in range(n):
        if st['next'] >= len(idx): print('NO MORE EPISODES'); break
        ep = idx[st['next']]
        path = build(ep)
        t = datetime.datetime.now(JST)
        vid = upload(yt, path, ep, t)
        st['posted'].setdefault('now-' + t.date().isoformat(), {})[t.strftime('%H%M%S')] = {'ep': ep, 'video': vid, 'at': t.isoformat()}
        st['next'] += 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1)
        print('URL https://youtube.com/shorts/' + vid, flush=True)
        shutil.rmtree(f'voice/{ep}', ignore_errors=True); os.remove(path)
    print('left in stock:', len(idx) - st['next'])

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'smoke'
    if cmd == 'daily': daily()
    elif cmd == 'smoke':
        p = build('ep01', seconds=3); print('smoke ok', os.path.getsize(p))
        if os.environ.get('YT_CLIENT_SECRET') and os.path.exists('rt.enc'): youtube(); print('channel ok')
    elif cmd == 'render': print(build(sys.argv[2]))
    elif cmd == 'now': now(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
