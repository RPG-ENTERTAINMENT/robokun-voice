"""CRAZY NINJA SHIZUKU しずく社長（YouTube @crazyninjajapan）— NINJA DIGITAL BAR で忍者しずくがチャレンジするショートを毎日1本 自動投稿（12:00 JST 予約公開）
  python ninja/main.py test [n]  -> 第n話を1本作って GitHub release「ninja-test」に置く（投稿しない）
  python ninja/main.py daily     -> 今日の1本を作って予約投稿
リポジトリのルートで実行（ninja/run.sh から呼ばれる）。台本は engine/gen.py が話数から自動で作る（6種類のチャレンジを順番に）。"""
import os, sys, json, subprocess, datetime, base64, hashlib
D = 'ninja'
sys.path.insert(0, os.path.join(D, 'engine'))
import gen  # noqa
JST = datetime.timezone(datetime.timedelta(hours=9))
SLOTS = [(12, 0)]
URL = 'https://www.rpgtokyo.com/ninjabar/'
TAGS = ['ninja', 'Ninja Shizuku', 'NINJA DIGITAL BAR', 'Tokyo', 'Japan', 'ninja challenge', 'Shinjuku', 'Shibuya',
        'things to do in Tokyo', 'Tokyo nightlife', 'kawaii', '忍者', 'しずく社長', 'shorts']
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)

def build(n, out):
    ep = gen.make(n)
    os.makedirs(f'{D}/out', exist_ok=True); os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    p = f'{D}/out/ep{n:03d}.json'; json.dump(ep, open(p, 'w'), ensure_ascii=False)
    sh('python', f'{D}/engine/render.py', p, out)
    return ep

def title(ep): return f"{ep['title']} 🥷 Ep.{ep['no']} #shorts"[:100]
def description(ep):
    return (f"{ep['title']}\nNinja Shizuku takes on a new ninja challenge every day at NINJA DIGITAL BAR in Tokyo! 🥷✨\n\n"
            "━━━━━━━━━━\n🏮 NINJA DIGITAL BAR (Tokyo)\n"
            "・Play ninja games with Ninja Shizuku — shuriken, sword and more\n"
            "・15 min from Shinjuku & Shibuya (near Meidaimae / Daitabashi)\n"
            "・Open 18:00–6:00 every day / English OK\n\n"
            f"▶ Website & booking: {URL}\n━━━━━━━━━━\n\n"
            "#ninja #Tokyo #Japan #NinjaShizuku #shorts\n\n"
            "Music & sound effects: original / Produced by RPG ENTERTAINMENT")

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
    from googleapiclient.http import MediaFileUpload
    status = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}
    now = datetime.datetime.now(datetime.timezone.utc)
    if when > now + datetime.timedelta(minutes=10): status['publishAt'] = when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else: status['privacyStatus'] = 'public'
    body = {'snippet': {'title': title(ep), 'description': description(ep)[:4900], 'tags': TAGS,
                        'categoryId': '24', 'defaultLanguage': 'en'}, 'status': status}
    try:
        resp = send(yt, body, path)
    except Exception as e:   # 細かい項目で弾かれたら、タイトル・説明・カテゴリだけで送り直す
        print('upload retry with minimal metadata:', e, flush=True)
        body['snippet'] = {'title': title(ep), 'description': description(ep)[:4900], 'categoryId': '24'}
        resp = send(yt, body, path)
    print('uploaded', ep['no'], resp['id'], status, flush=True); return resp['id']

def daily():
    if not os.path.exists(f'{D}/rt.enc'): print('YouTube not connected yet (ninja:auth_url / auth_code) - skipping'); return
    now = datetime.datetime.now(JST); day = (now + datetime.timedelta(hours=3)).date()   # 21時以降の実行は翌日ぶん
    st_path = f'{D}/state/state.json'; os.makedirs(f'{D}/state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 1, 'posted': {}}
    key = day.isoformat(); done = st['posted'].setdefault(key, {}); yt = youtube()
    for slot, (h, m) in enumerate(SLOTS):
        when = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
        if str(slot) in done: print('slot already posted', key, slot); continue
        if when < datetime.datetime.now(JST) - datetime.timedelta(hours=2): print('slot time passed, skip', key, slot); continue
        n = st['next']; path = f'{D}/out/ninja_{key}_{slot}.mp4'
        ep = build(n, path); vid = upload(yt, path, ep, when)
        done[str(slot)] = {'ep': n, 'video': vid, 'at': when.isoformat()}; st['next'] = n + 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1); os.remove(path)

def test(n=None):
    st_path = f'{D}/state/state.json'
    n = int(n) if n else (json.load(open(st_path))['next'] if os.path.exists(st_path) else 1)
    out = f'{D}/out/ninja_test_{n:03d}.mp4'; build(n, out)
    subprocess.run(['gh', 'release', 'delete', 'ninja-test', '-y', '--cleanup-tag'])
    sh('gh', 'release', 'create', 'ninja-test', out, '--title', f'ninja test ep{n:03d}', '--notes', f'ep{n:03d}', '--prerelease')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'test'
    if cmd == 'daily': daily()
    elif cmd == 'test': test(sys.argv[2] if len(sys.argv) > 2 else None)
