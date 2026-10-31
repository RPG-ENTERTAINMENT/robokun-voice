"""大道芸専門アカデミー（YouTube @daidogeisenmon）— ロボしずの大道芸ショートを毎日2本 自動投稿（12:00 / 20:00 JST 予約公開）
  python daido/main.py test [id]  -> 1本作って GitHub release「daido-test」に置く（投稿しない）
  python daido/main.py daily      -> 今日の2本を作って予約投稿
リポジトリのルートで実行（daido/run.sh から呼ばれる）。ネタは daido/episodes/*.json、順番は daido/index.json。"""
import os, sys, json, glob, shutil, subprocess, datetime, base64, hashlib
D = 'daido'
JST = datetime.timezone(datetime.timedelta(hours=9))
SLOTS = [(12, 0), (20, 0)]
URL = 'https://rpgtokyo.com/daidogei/'
LINE = 'https://lin.ee/zuMn2H1'
TAGS = ['大道芸', '大道芸専門アカデミー', 'ジャグリング', 'パフォーマー', 'ロボしず', 'ショートアニメ', 'shorts']
def sh(*a, **k): print('+', ' '.join(a), flush=True); return subprocess.run(a, check=True, **k)

def build(eid, out):
    shutil.copy(f'{D}/episodes/{eid}.json', f'episodes/{eid}.json')   # robo_tts.py は episodes/ から読む
    shutil.rmtree(f'vo/{eid}', ignore_errors=True)
    sh('python', 'scripts/robo_tts.py', eid)
    sh('python', 'eng/tts_vv.py', f'episodes/{eid}.json', f'vo/{eid}', '--vv', 'vv', '--skip-robo')
    for w in glob.glob(f'vo/{eid}/[0-9][0-9].wav'):   # ショートは少しテンポよく
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-af', 'atempo=1.1', w+'.f.wav'], check=True); os.replace(w+'.f.wav', w)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    env = dict(os.environ, ROBO_ASSETS=os.path.abspath('assets')+'/')
    sh('python', 'eng/engine_l.py', f'episodes/{eid}.json', f'vo/{eid}', out, '--procs', str(os.cpu_count() or 2), env=env)
    return json.load(open(f'{D}/episodes/{eid}.json'))

def title(ep): return f"{ep.get('yt_title') or ep['title']}｜大道芸専門アカデミー #shorts"[:100]
def description(ep):
    return (f"{ep.get('yt_title') or ep['title']}\nロボしずが大道芸に挑戦するショートアニメ🎪\n\n"
            "━━━━━━━━━━\n🎪 大道芸専門アカデミー 生徒募集中\n"
            "・静岡大道芸の元出演者が、毎週オンラインであなたのショーをチェック\n"
            "・全国どこからでも、好きな時間に受講OK\n・仕事につなげる就職コースあり\n・月々25,000円から\n\n"
            f"▶ 詳しく・無料相談：{URL}\n▶ LINEで相談：{LINE}\n━━━━━━━━━━\n\n"
            "#大道芸 #ジャグリング #パフォーマー #大道芸専門アカデミー #shorts\n\n"
            "音声合成：VOICEVOX:雨晴はう／VOICEVOX:No.7\nロボしずの声：ロボットしずく（本人）\n制作：株式会社RPGエンターテイメント")

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
    if want and want not in mine: raise SystemExit(f'WRONG CHANNEL: token is for {mine}, expected {want}. Not uploading.')
    return yt

def upload(yt, path, ep, when):
    from googleapiclient.http import MediaFileUpload
    status = {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False}
    now = datetime.datetime.now(datetime.timezone.utc)
    if when > now + datetime.timedelta(minutes=10): status['publishAt'] = when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else: status['privacyStatus'] = 'public'
    body = {'snippet': {'title': title(ep), 'description': description(ep)[:4900], 'tags': TAGS,
                        'categoryId': '24', 'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'}, 'status': status}
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    print('uploaded', ep['id'], resp['id'], status, flush=True); return resp['id']

def daily():
    if not os.path.exists(f'{D}/rt.enc'): print('YouTube not connected yet (daido:auth_url / auth_code) - skipping'); return
    idx = json.load(open(f'{D}/index.json')); n = len(idx)
    now = datetime.datetime.now(JST); day = (now + datetime.timedelta(hours=3)).date()   # 21時以降の実行は翌日ぶん
    st_path = f'{D}/state/state.json'; os.makedirs(f'{D}/state', exist_ok=True)
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'posted': {}}
    key = day.isoformat(); done = st['posted'].setdefault(key, {}); yt = youtube()
    for slot, (h, m) in enumerate(SLOTS):
        when = datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
        if str(slot) in done: print('slot already posted', key, slot); continue
        if when < datetime.datetime.now(JST) - datetime.timedelta(hours=2): print('slot time passed, skip', key, slot); continue
        eid = idx[st['next'] % n]; path = f'out/daido_{key}_{slot}.mp4'
        ep = build(eid, path); vid = upload(yt, path, ep, when)
        done[str(slot)] = {'ep': eid, 'video': vid, 'at': when.isoformat()}; st['next'] += 1
        json.dump(st, open(st_path, 'w'), ensure_ascii=False, indent=1); os.remove(path)
    if st['next'] >= n - 2: print('NOTE: ネタ帳が残りわずか（daido/episodes に追加してください）')

def test(eid=None):
    eid = eid or json.load(open(f'{D}/index.json'))[0]; out = f'out/daido_test_{eid}.mp4'
    build(eid, out)
    subprocess.run(['gh', 'release', 'delete', 'daido-test', '-y', '--cleanup-tag'])
    sh('gh', 'release', 'create', 'daido-test', out, '--title', f'daido test {eid}', '--notes', eid, '--prerelease')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'test'
    if cmd == 'daily': daily()
    elif cmd == 'test': test(sys.argv[2] if len(sys.argv) > 2 else None)
