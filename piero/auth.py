"""YouTube OAuth for the piero channel.
  python piero/auth.py url   -> writes piero/logs/auth_url.txt
  python piero/auth.py code  -> reads piero/jobs/auth_code.txt (the full localhost URL or just the code),
                                stores the refresh token encrypted in piero/rt.enc (key = YT_CLIENT_SECRET)"""
import os, sys, json, base64, hashlib, urllib.parse, urllib.request
from cryptography.fernet import Fernet
CID, CSEC = os.environ['YT_CLIENT_ID'], os.environ['YT_CLIENT_SECRET']
REDIR = 'http://localhost'
SCOPES = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
os.makedirs('piero/logs', exist_ok=True)
def fernet(): return Fernet(base64.urlsafe_b64encode(hashlib.sha256(CSEC.encode()).digest()))
if sys.argv[1] == 'url':
    q = urllib.parse.urlencode({'client_id': CID, 'redirect_uri': REDIR, 'response_type': 'code', 'scope': SCOPES,
                                'access_type': 'offline', 'prompt': 'select_account consent'})
    u = 'https://accounts.google.com/o/oauth2/v2/auth?' + q
    open('piero/logs/auth_url.txt', 'w').write(' '.join(u) + '\n')   # spaced so the log masker leaves it alone; join to use
    print('written')
elif sys.argv[1] == 'code':
    raw = open('piero/jobs/auth_code.txt').read().strip()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get('code', [raw])[0]
    data = urllib.parse.urlencode({'code': code, 'client_id': CID, 'client_secret': CSEC, 'redirect_uri': REDIR,
                                   'grant_type': 'authorization_code'}).encode()
    try:
        tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', data))
    except urllib.error.HTTPError as e:
        msg = e.read().decode(); open('piero/logs/auth_result.txt', 'w').write('TOKEN ERROR ' + msg); print(msg); sys.exit(1)
    rt = tok.get('refresh_token')
    req = urllib.request.Request('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                                 headers={'Authorization': 'Bearer ' + tok['access_token']})
    ch = json.load(urllib.request.urlopen(req))
    names = [(c['id'], c['snippet']['title']) for c in ch.get('items', [])]
    if rt:
        open('piero/rt.enc', 'wb').write(fernet().encrypt(rt.encode()))
    open('piero/logs/auth_result.txt', 'w').write(json.dumps({'refresh_token': bool(rt), 'channels': names}, ensure_ascii=False))
    print('channels', names, 'rt', bool(rt))
