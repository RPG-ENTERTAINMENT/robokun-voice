"""スゴ技スクールRPG 宣伝ショート — 毎日2本 自動投稿（7:00 / 18:00 JST）
  python main.py daily        -> 今日の2本を作って予約投稿
  python main.py smoke        -> 動作確認（声＋短い描画、投稿なし）
  python main.py render <id>  -> 1本だけ作る（投稿なし） out/<id>.mp4
sugo/ ディレクトリで実行する。"""
import os, sys, json, subprocess, datetime, shutil, base64, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = datetime.timezone(datetime.timedelta(hours=9))
SLOTS = [(7, 0), (18, 0)]
def sh(*a): print('+', ' '.join(a), flush=True); subprocess.run(a, check=True)

def build(eid, out=None):
    import episodes, chara
    shutil.rmtree('voice', ignore_errors=True)
    sh(sys.executable, 'voices.py', str(eid))
    ep = next(e for e in episodes.EPISODES if e['id'] == eid)
    os.makedirs('out', exist_ok=True); out = out or f'out/{eid}.mp4'
    dur = chara.render_voiced(ep, out); print('rendered', eid, f'{dur:.1f}s', os.path.getsize(out) // 1024, 'KB', flush=True)
    return ep, out

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
    want = open('channel_id.txt').read().strip() if os.path.exists('channel_id.txt') else ''
    if want and want not in mine: raise SystemExit(f'WRONG CHANNEL: token is for {mine}, expected {want}. Not uploading.')
    return yt

def upload(yt, path, ep, when):
    import episodes
    from googleapiclient.http import MediaFileUpload
    status = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': True}
    now = datetime.datetime.now(datetime.timezone.utc)
    if when > now + datetime.timedelta(minutes=10): status['publishAt'] = when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else: status['privacyStatus'] = 'public'
    body = {'snippet': {'title': ep['title'][:100], 'description': episodes.description(ep)[:4900], 'tags': episodes.tags(ep),
                        'categoryId': '27', 'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    print('uploaded', ep['id'], resp['id'], status, flush=True); return resp['id']

def daily():
    if not os.path.exists('rt.enc'): print('YouTube not connected yet (run sugo:auth_url / sugo:auth_code first) - skipping'); return
    import episodes
    now = datetime.datetime.now(JST); day = (now + datetime.timedelta(hours=4)).date()   # 20時以降は翌日ぶんを用意
    st_path = 'state/state.json'; os.makedirs('state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'posted': {}}
    key = day.isoformat(); done = st['posted'].setdefault(key, {}); yt = youtube(); n = len(episodes.EPISODES)
    for slot, (h, m) in enumerate(SLOTS):
        if str(slot) in done: print('slot already posted', key, slot); continue
        ep0 = episodes.EPISODES[st['next'] % n]
        ep, path = build(ep0['id'])
        when = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
        vid = upload(yt, path, ep, when)
        done[str(slot)] = {'ep': ep['id'], 'video': vid, 'at': when.isoformat()}; st['next'] += 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1); os.remove(path)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'smoke'
    if cmd == 'daily': daily()
    elif cmd == 'smoke':
        ep, p = build(1); print('smoke ok', os.path.getsize(p))
        if os.environ.get('YT_CLIENT_SECRET') and os.path.exists('rt.enc'): youtube(); print('channel ok')
    elif cmd == 'render': build(int(sys.argv[2]))
