"""Post today's slot (A=12:00, B=19:00 JST) to the configured SNS."""
import os, sys, json, subprocess, datetime, argparse, glob, time
ap = argparse.ArgumentParser(); ap.add_argument('--slot', required=True); g = ap.parse_args()
JST = datetime.timezone(datetime.timedelta(hours=9)); _now = datetime.datetime.now(JST)
# GitHub's scheduled runs are often hours late: a 19:00 post can start after midnight JST.
# Before 06:00 JST, the slot still belongs to the previous day.
day = (_now - datetime.timedelta(hours=6)).strftime('%Y%m%d')
tag = f'day-{day}'; os.makedirs('dl', exist_ok=True)
subprocess.run(['gh', 'release', 'download', tag, '-D', 'dl', '--clobber'], check=True)
meta = json.load(open('dl/meta.json')); epid = meta[g.slot]
vid = glob.glob(f'dl/*_{g.slot}_{epid}.mp4')[0]
ep = json.load(open(f'episodes/{epid}.json'))
title = f"{ep['title']}｜ロボしず #shorts"
st_path = 'state/posted.json'; os.makedirs('state', exist_ok=True)
posted = json.load(open(st_path)) if os.path.exists(st_path) else {}
key = f'{day}{g.slot}'; posted.setdefault(key, {})
results = {}
# ---------------- YouTube
if os.environ.get('YT_REFRESH_TOKEN') and 'youtube' not in posted[key]:
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        yc = json.load(open('config/youtube.json'))
        cr = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], token_uri='https://oauth2.googleapis.com/token',
                         client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'],
                         scopes=['https://www.googleapis.com/auth/youtube.upload'])
        yt = build('youtube', 'v3', credentials=cr)
        body = {'snippet': {'title': title[:100], 'description': yc['description'], 'tags': yc['tags'], 'categoryId': yc['category'], 'defaultLanguage': 'ja'},
                'status': {'privacyStatus': yc['privacy'], 'selfDeclaredMadeForKids': yc['made_for_kids'], 'containsSyntheticMedia': False}}
        req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(vid, mimetype='video/mp4', resumable=True))
        resp = None
        while resp is None: _, resp = req.next_chunk()
        posted[key]['youtube'] = resp['id']; print('youtube ok', resp['id'], resp.get('status'))
    except Exception as e:
        print('youtube FAILED', repr(e)); results['youtube_error'] = repr(e)
# ---------------- Instagram (Reels) -- needs a public video URL: use the release asset URL
if os.environ.get('IG_TOKEN') and os.environ.get('IG_USER_ID') and 'instagram' not in posted[key]:
    try:
        import requests
        V = 'https://graph.facebook.com/v21.0'; tok = os.environ['IG_TOKEN']; uid = os.environ['IG_USER_ID']
        cap = f"{ep['title']}\n\n" + json.load(open('config/youtube.json'))['description']
        c = requests.post(f'{V}/{uid}/media', data={'media_type': 'REELS', 'upload_type': 'resumable', 'caption': cap, 'access_token': tok}).json()
        cid = c['id']; size = os.path.getsize(vid)
        up = requests.post(f'https://rupload.facebook.com/ig-api-upload/v21.0/{cid}', headers={'Authorization': f'OAuth {tok}', 'offset': '0', 'file_size': str(size)}, data=open(vid, 'rb')).json()
        print('ig upload', up)
        for _ in range(60):
            s = requests.get(f'{V}/{cid}', params={'fields': 'status_code', 'access_token': tok}).json()
            if s.get('status_code') == 'FINISHED': break
            time.sleep(10)
        p = requests.post(f'{V}/{uid}/media_publish', data={'creation_id': cid, 'access_token': tok}).json()
        posted[key]['instagram'] = p.get('id'); print('instagram', p)
    except Exception as e:
        print('instagram FAILED', repr(e))
# ---------------- TikTok (Direct Post; private until the TikTok app passes its audit)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tiktok
if tiktok.configured() and not ({'tiktok', 'tiktok_private'} & set(posted[key])):
    try:
        tags = ' '.join('#' + t for t in json.load(open('config/youtube.json'))['tags'] if t != 'shorts')
        r = tiktok.post(vid, f"{ep['title']}｜ロボしず {tags}")
        if r.get('privacy') == 'PUBLIC_TO_EVERYONE': posted[key]['tiktok'] = r['publish_id']
        else: posted[key]['tiktok_private'] = r['publish_id']
    except Exception as e:
        print('tiktok FAILED', repr(e))
json.dump(posted, open(st_path, 'w'), ensure_ascii=False, indent=1)
