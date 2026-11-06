"""Delete videos listed in piero/jobs/delete_ids.txt (one video ID per line) from the piero channel.
Each video is checked to belong to the piero channel before deleting. Result -> piero/logs/delete_result.json.
Needs the youtube.force-ssl scope (added 2026-11-06). Run: jobs/daily_task = piero:py:delete"""
import os, sys, json, base64, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

path = os.path.join(ROOT, 'jobs', 'delete_ids.txt')
ids = [l.strip() for l in open(path) if l.strip() and not l.startswith('#')]
res = []
for k in range(0, len(ids), 50):
    chunk = ids[k:k + 50]
    found = {v['id']: v for v in yt.videos().list(part='snippet,statistics', id=','.join(chunk)).execute().get('items', [])}
    for vid in chunk:
        v = found.get(vid)
        if not v: res.append(dict(id=vid, result='not found')); continue
        if v['snippet']['channelId'] != CHANNEL_ID: res.append(dict(id=vid, result='other channel - skipped')); continue
        row = dict(id=vid, title=v['snippet']['title'], views=int(v.get('statistics', {}).get('viewCount', 0)))
        try:
            yt.videos().delete(id=vid).execute(); row['result'] = 'deleted'
        except Exception as e:
            row['result'] = 'error ' + repr(e)[:200]
        res.append(row); print(row)
json.dump(dict(at=datetime.datetime.utcnow().isoformat(), results=res), open(os.path.join(ROOT, 'logs', 'delete_result.json'), 'w'), ensure_ascii=False, indent=1)
os.remove(path)
print('deleted', sum(r['result'] == 'deleted' for r in res), 'of', len(ids))
# refresh the stats file afterwards (read-only)
import stats  # noqa: F401  (writes piero/logs/stats.json)
