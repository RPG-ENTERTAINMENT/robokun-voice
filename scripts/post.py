"""Post today's slot (A=12:00, B=19:00 JST) to the configured SNS."""
import os, sys, json, subprocess, datetime, argparse, glob, time
ap = argparse.ArgumentParser(); ap.add_argument('--slot', required=True); g = ap.parse_args()
JST = datetime.timezone(datetime.timedelta(hours=9)); day = datetime.datetime.now(JST).strftime('%Y%m%d')
tag = f'day-{day}'; os.makedirs('dl', exist_ok=True)
subprocess.run(['gh', 'release', 'download', tag, '-D', 'dl', '--clobber'], check=True)
meta = json.load(open('dl/meta.json')); epid = meta[g.slot]
vid = glob.glob(f'dl/*_{g.slot}_{epid}.mp4')[0]
ep = json.load(open(f'episodes/{epid}.json'))
title = f"{ep['title']}｜ロボくん #shorts"
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
                'status': {'privacyStatus': yc['privacy'], 'selfDeclaredMadeForKids': yc['made_for_kids'], 'containsSyntheticMedia': True}}
        req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(vid, mimetype='video/mp4', resumable=True))
        resp = None
        while resp is None: _, resp = req.next_chunk()
        posted[key]['youtube'] = resp['id']; print('youtube ok', resp['id'], resp.get('status'))
    except Exception as e:
        print('youtube FAILED', repr(e)); results['youtube_error'] = repr(e)
# ---------------- Instagram (Reels, resumable upload)
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
json.dump(posted, open(st_path, 'w'), ensure_ascii=False, indent=1)
