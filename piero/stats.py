"""Write view/like stats of every upload on the piero channel to piero/logs/stats.json (read-only)."""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as M

yt = M.yt_client()
ch = yt.channels().list(part='contentDetails,statistics', mine=True).execute()['items'][0]
up = ch['contentDetails']['relatedPlaylists']['uploads']
ids, tok = [], None
while True:
    r = yt.playlistItems().list(part='contentDetails', playlistId=up, maxResults=50, pageToken=tok).execute()
    ids += [i['contentDetails']['videoId'] for i in r['items']]
    tok = r.get('nextPageToken')
    if not tok: break
rows = []
for k in range(0, len(ids), 50):
    r = yt.videos().list(part='snippet,statistics,contentDetails,status', id=','.join(ids[k:k + 50])).execute()
    for v in r['items']:
        s = v.get('statistics', {})
        rows.append(dict(id=v['id'], title=v['snippet']['title'], published=v['snippet'].get('publishedAt'),
                         status=v['status'].get('privacyStatus'), dur=v['contentDetails'].get('duration'),
                         views=int(s.get('viewCount', 0)), likes=int(s.get('likeCount', 0)), comments=int(s.get('commentCount', 0))))
rows.sort(key=lambda x: x['published'] or '')
out = dict(at=datetime.datetime.utcnow().isoformat(), channel=ch['statistics'], videos=rows)
json.dump(out, open(os.path.join(M.ROOT, 'logs', 'stats.json'), 'w'), ensure_ascii=False, indent=1)
print('channel', ch['statistics']); [print(r['published'][:16], r['views'], r['likes'], r['dur'], r['title'][:40]) for r in rows]
