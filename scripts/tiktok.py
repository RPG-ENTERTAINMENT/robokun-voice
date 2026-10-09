"""TikTok Content Posting API (Direct Post) for the robokun shorts.

The repo is public, so the TikTok refresh token is never written in clear text:
it is kept in state/tt_token.enc, encrypted with the TT_CLIENT_SECRET secret.

  python scripts/tiktok.py auth <code>      # one-time: exchange the code from rpgtokyo.com/tiktok-auth/
  python scripts/tiktok.py post <mp4> <title>
"""
import os, sys, json, time, subprocess, requests

API = 'https://open.tiktokapis.com/v2'
REDIRECT = 'https://www.rpgtokyo.com/tiktok-auth/'
ENC = 'state/tt_token.enc'


def _key():
    return os.environ['TT_CLIENT_KEY'], os.environ['TT_CLIENT_SECRET']


def _save_refresh(tok):
    os.makedirs('state', exist_ok=True)
    r = subprocess.run(['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-a', '-A', '-pass', 'env:TT_CLIENT_SECRET'],
                       input=tok.encode(), capture_output=True, check=True)
    open(ENC, 'wb').write(r.stdout)


def _load_refresh():
    if os.path.exists(ENC):
        r = subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-a', '-A', '-pass', 'env:TT_CLIENT_SECRET', '-in', ENC],
                           capture_output=True, check=True)
        return r.stdout.decode().strip()
    return os.environ.get('TT_REFRESH_TOKEN') or None


def configured():
    return bool(os.environ.get('TT_CLIENT_KEY') and os.environ.get('TT_CLIENT_SECRET') and _load_refresh())


def _token(data):
    ck, cs = _key()
    r = requests.post(f'{API}/oauth/token/', data=dict(data, client_key=ck, client_secret=cs),
                      headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    if 'access_token' not in r:
        raise RuntimeError(f'token error: {r.get("error")} {r.get("error_description")}')
    _save_refresh(r['refresh_token'])   # TikTok may rotate it; always keep the newest
    return r


def auth(code):
    r = _token({'code': code, 'grant_type': 'authorization_code', 'redirect_uri': REDIRECT})
    print('tiktok auth ok; scope =', r.get('scope'), '; refresh valid for', r.get('refresh_expires_in'), 's')


def access_token():
    return _token({'grant_type': 'refresh_token', 'refresh_token': _load_refresh()})['access_token']


def post(mp4, title):
    at = access_token()
    H = {'Authorization': f'Bearer {at}', 'Content-Type': 'application/json; charset=UTF-8'}
    info = requests.post(f'{API}/post/publish/creator_info/query/', headers=H).json()
    opts = (info.get('data') or {}).get('privacy_level_options') or ['SELF_ONLY']
    print('tiktok creator', (info.get('data') or {}).get('creator_username'), opts)
    want = os.environ.get('TT_PRIVACY', 'PUBLIC_TO_EVERYONE')
    size = os.path.getsize(mp4)

    def init(level):
        body = {'post_info': {'title': title[:2200], 'privacy_level': level, 'disable_duet': False,
                              'disable_comment': False, 'disable_stitch': False, 'video_cover_timestamp_ms': 0},
                'source_info': {'source': 'FILE_UPLOAD', 'video_size': size, 'chunk_size': size, 'total_chunk_count': 1}}
        return requests.post(f'{API}/post/publish/video/init/', headers=H, json=body).json()

    level = want if want in opts else ('PUBLIC_TO_EVERYONE' if 'PUBLIC_TO_EVERYONE' in opts else opts[0])
    r = init(level)
    if r.get('error', {}).get('code') == 'unaudited_client_can_only_post_to_private_accounts' and level != 'SELF_ONLY':
        print('tiktok: app not audited yet -> posting as SELF_ONLY (private)')
        level = 'SELF_ONLY'; r = init(level)
    if r.get('error', {}).get('code') not in (None, 'ok'):
        raise RuntimeError(f'init error: {r["error"]}')
    pid, url = r['data']['publish_id'], r['data']['upload_url']
    up = requests.put(url, data=open(mp4, 'rb').read(),
                      headers={'Content-Type': 'video/mp4', 'Content-Length': str(size), 'Content-Range': f'bytes 0-{size-1}/{size}'})
    up.raise_for_status()
    status = None
    for _ in range(60):
        time.sleep(10)
        s = requests.post(f'{API}/post/publish/status/fetch/', headers=H, json={'publish_id': pid}).json()
        status = (s.get('data') or {}).get('status')
        if status in ('PUBLISH_COMPLETE', 'FAILED'):
            if status == 'FAILED': raise RuntimeError(f'publish failed: {s}')
            break
    print('tiktok', level, pid, status)
    return {'publish_id': pid, 'privacy': level, 'status': status}


if __name__ == '__main__':
    if sys.argv[1] == 'auth': auth(sys.argv[2])
    elif sys.argv[1] == 'post': print(post(sys.argv[2], sys.argv[3]))
