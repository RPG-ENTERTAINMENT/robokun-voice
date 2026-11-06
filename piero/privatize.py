"""Make videos listed in piero/jobs/private_ids.txt private (and cancel any scheduled publish time).
Each video is checked to belong to the piero channel first. Result -> piero/logs/private_result.json.
Needs the youtube.force-ssl scope (added 2026-11-06). Run: jobs/daily_task = piero:py:privatize"""
import os, sys, json, base64, hashlib, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
CHANNEL_ID = 'UCiQrLGBmriz6p2NACHI33eg'
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sec = os.environ['YT_CLIENT_SECRET']
rt = Fernet(base64.urlsafe_b64encode(hashlib.sha256(sec.encode()).digest())).decrypt(open(os.path.join(ROOT, 'rt.enc'), 'rb').read()).decode()
cr = Credentials(None, refresh_token=rt, token_uri='https://oauth2.googleapis.com/token', client_id=os.environ['YT_CLIENT_ID'], client_secret=sec)
yt = build('youtube', 'v3', credentials=cr)
mine = [c['id'] for c in yt.channels().list(part='id', mine=True).execute().get('items', [])]
if CHANNEL_ID not in mine: raise SystemExit(f'wrong channel: {mine}')

path = os.path.join(ROOT, 'jobs', 'private_ids.txt')
ids = [l.strip() for l in open(path) if l.strip() and not l.startswith('#')]
res = []
for vid in ids:
    items = yt.videos().list(part='snippet,status', id=vid).execute().get('items', [])
    if not items: res.append(dict(id=vid, result='not found')); continue
    v = items[0]
    if v['snippet']['channelId'] != CHANNEL_ID: res.append(dict(id=vid, result='other channel - skipped')); continue
    st = {k: v['status'][k] for k in ('embeddable', 'license', 'publicStatsViewable', 'selfDeclaredMadeForKids') if k in v['status']}
    st['privacyStatus'] = 'private'   # no publishAt -> the scheduled publish is cancelled
    try:
        r = yt.videos().update(part='status', body={'id': vid, 'status': st}).execute()
        res.append(dict(id=vid, title=v['snippet']['title'], result='private', publishAt=r['status'].get('publishAt')))
    except Exception as e:
        res.append(dict(id=vid, title=v['snippet']['title'], result='error ' + repr(e)[:200]))
    print(res[-1])
json.dump(dict(at=datetime.datetime.utcnow().isoformat(), results=res), open(os.path.join(ROOT, 'logs', 'private_result.json'), 'w'), ensure_ascii=False, indent=1)
os.remove(path)
