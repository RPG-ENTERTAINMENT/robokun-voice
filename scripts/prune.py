"""ロボしず (@roboshizu): 投稿から3日たっても再生数が100回未満の公開動画を「非公開」にする（削除はしない）。
  python scripts/prune.py dry        -> 対象を一覧にするだけ（何も変えない）
  python scripts/prune.py run        -> 対象を非公開にする
  python scripts/prune.py auth_url   -> logs/prune_auth_url.txt（開いて ロボしず チャンネルを選ぶ）
  python scripts/prune.py auth_code  -> jobs/prune_code.txt を読んで state/yt_rt.enc に保存
しきい値は config/prune.json（days / min_views / enabled）で変えられる。
非公開にした動画は state/pruned.json に記録。YouTube Studio で公開に戻せる。"""
import os, sys, json, base64, hashlib, datetime, urllib.parse, urllib.request
os.makedirs('logs', exist_ok=True); os.makedirs('state', exist_ok=True)
CID, CSEC = os.environ['YT_CLIENT_ID'], os.environ['YT_CLIENT_SECRET']
REDIR = 'https://developers.google.com/oauthplayground'
SCOPE = 'https://www.googleapis.com/auth/youtube'   # 公開設定の変更に必要
RT_FILE = 'state/yt_rt.enc'
cfg = {'enabled': True, 'days': 3, 'min_views': 100, 'channel_handle': '@roboshizu'}
if os.path.exists('config/prune.json'): cfg.update(json.load(open('config/prune.json')))
mode = sys.argv[1] if len(sys.argv) > 1 else 'dry'

def fernet():
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(CSEC.encode()).digest()))

if mode == 'auth_url':
    q = urllib.parse.urlencode({'client_id': CID, 'redirect_uri': REDIR, 'response_type': 'code', 'scope': SCOPE,
                                'access_type': 'offline', 'prompt': 'select_account consent'})
    open('logs/prune_auth_url.txt', 'w').write(' '.join('https://accounts.google.com/o/oauth2/v2/auth?' + q) + '\n')
    print('written'); sys.exit(0)
if mode == 'auth_code':
    raw = open('jobs/prune_code.txt').read().strip()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get('code', [raw])[0]
    data = urllib.parse.urlencode({'code': code, 'client_id': CID, 'client_secret': CSEC, 'redirect_uri': REDIR,
                                   'grant_type': 'authorization_code'}).encode()
    try: tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', data))
    except urllib.error.HTTPError as e:
        open('logs/prune_auth_result.txt', 'w').write('TOKEN ERROR ' + e.read().decode()); sys.exit(1)
    req = urllib.request.Request('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                                 headers={'Authorization': 'Bearer ' + tok['access_token']})
    names = [(c['id'], c['snippet']['title'], c['snippet'].get('customUrl')) for c in json.load(urllib.request.urlopen(req)).get('items', [])]
    rt = tok.get('refresh_token')
    if rt: open(RT_FILE, 'wb').write(fernet().encrypt(rt.encode()))
    open('logs/prune_auth_result.txt', 'w').write(json.dumps({'refresh_token': bool(rt), 'channels': names}, ensure_ascii=False))
    print(names, bool(rt)); sys.exit(0)

# ---------------- dry / run
if not cfg.get('enabled', True): print('prune disabled'); sys.exit(0)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
if os.path.exists(RT_FILE): rt = fernet().decrypt(open(RT_FILE, 'rb').read()).decode()
else: rt = os.environ['YT_REFRESH_TOKEN']
yt = build('youtube', 'v3', credentials=Credentials(None, refresh_token=rt, token_uri='https://oauth2.googleapis.com/token',
                                                    client_id=CID, client_secret=CSEC))
ch = yt.channels().list(part='snippet,contentDetails', mine=True).execute()['items'][0]
handle = (ch['snippet'].get('customUrl') or '').lower()
if handle != cfg['channel_handle'].lower():
    print('STOP: channel is', handle, ch['snippet']['title']); sys.exit(1)   # ロボしず以外のチャンネルには絶対に触らない
uploads = ch['contentDetails']['relatedPlaylists']['uploads']
ids, tok = [], None
while True:
    r = yt.playlistItems().list(part='contentDetails', playlistId=uploads, maxResults=50, pageToken=tok).execute()
    ids += [i['contentDetails']['videoId'] for i in r['items']]
    tok = r.get('nextPageToken')
    if not tok: break
now = datetime.datetime.now(datetime.timezone.utc); limit = now - datetime.timedelta(days=cfg['days'])
pruned_path = 'state/pruned.json'
pruned = json.load(open(pruned_path)) if os.path.exists(pruned_path) else {}
keep = set(cfg.get('keep', []))   # 例外にしたい動画ID
targets = []
for k in range(0, len(ids), 50):
    for v in yt.videos().list(part='snippet,status,statistics', id=','.join(ids[k:k+50])).execute()['items']:
        if v['status']['privacyStatus'] != 'public' or v['id'] in keep: continue
        pub = datetime.datetime.fromisoformat(v['snippet']['publishedAt'].replace('Z', '+00:00'))
        views = int(v['statistics'].get('viewCount', 0))
        if pub < limit and views < cfg['min_views']: targets.append((v, views))
print(f'public videos checked: {len(ids)}  targets: {len(targets)}  mode: {mode}')
for v, views in targets:
    line = f"{v['id']}  {views}回  {v['snippet']['publishedAt'][:10]}  {v['snippet']['title']}"
    if mode == 'run':
        try:
            body = {'id': v['id'], 'status': {k: v['status'][k] for k in ('embeddable', 'license', 'publicStatsViewable', 'selfDeclaredMadeForKids') if k in v['status']}}
            body['status']['privacyStatus'] = 'private'
            yt.videos().update(part='status', body=body).execute()
            pruned[v['id']] = {'views': views, 'title': v['snippet']['title'], 'published': v['snippet']['publishedAt'], 'at': now.isoformat()}
            print('PRIVATE', line)
        except Exception as e:
            print('FAILED', line, repr(e))
            if 'insufficient' in repr(e).lower(): print('need re-auth: task prune:auth_url'); break
    else:
        print('would', line)
json.dump(pruned, open(pruned_path, 'w'), ensure_ascii=False, indent=1)
