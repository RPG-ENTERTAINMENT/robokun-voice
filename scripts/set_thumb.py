"""Set a custom thumbnail on an existing YouTube video: set_thumb.py VIDEO_ID image.png"""
import os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
vid, img = sys.argv[1:3]
cr = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], token_uri='https://oauth2.googleapis.com/token',
                 client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'],
                 scopes=['https://www.googleapis.com/auth/youtube.upload'])
yt = build('youtube', 'v3', credentials=cr)
try:
    r = yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(img, mimetype='image/png')).execute()
    print('thumbnail ok', r.get('items', [{}])[0].get('default', {}).get('url'))
except Exception as e:
    print('thumbnail FAILED', repr(e)[:400]); sys.exit(1)
