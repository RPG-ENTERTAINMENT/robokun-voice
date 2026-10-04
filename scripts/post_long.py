"""Upload a long (landscape) video to YouTube with its own metadata + thumbnail."""
import os, sys, json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
vid, thumb, meta = sys.argv[1:4]
m = json.load(open(meta))
import subprocess
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', vid], capture_output=True, text=True).stdout or 0)
print('duration', dur)
if not (m.get('min_dur', 0) <= dur <= m.get('max_dur', 1e9)): sys.exit('duration check failed, not uploading')
cr = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], token_uri='https://oauth2.googleapis.com/token',
                 client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'],
                 scopes=['https://www.googleapis.com/auth/youtube.upload'])
yt = build('youtube', 'v3', credentials=cr)
body = {'snippet': {'title': m['title'][:100], 'description': m['description'], 'tags': m['tags'], 'categoryId': m.get('category', '1'),
                    'defaultLanguage': 'ja', 'defaultAudioLanguage': 'ja'},
        'status': {'privacyStatus': m.get('privacy', 'public'), 'selfDeclaredMadeForKids': m.get('made_for_kids', False), 'containsSyntheticMedia': False}}
if m.get('publish_at'): body['status'].update(privacyStatus='private', publishAt=m['publish_at']); print('scheduled for', m['publish_at'])
req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(vid, mimetype='video/mp4', resumable=True, chunksize=16*1024*1024))
resp = None
while resp is None:
    st, resp = req.next_chunk()
    if st: print('upload', int(st.progress()*100), '%', flush=True)
vid_id = resp['id']; print('youtube ok', vid_id, resp.get('status'), flush=True)
try:
    yt.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumb, mimetype='image/png')).execute(); print('thumbnail ok')
except Exception as e:
    print('thumbnail FAILED (channel may need phone verification)', repr(e)[:300])
os.makedirs('state', exist_ok=True)
p = 'state/long_posted.json'; d = json.load(open(p)) if os.path.exists(p) else {}
d[os.path.basename(meta)] = vid_id; json.dump(d, open(p, 'w'), indent=1)
