"""Fetch free-licence photos (Openverse / Wikimedia Commons: CC0, PDM, CC BY) for a job file.
usage: python3 scripts/fetch_imgs.py <job>   (reads jobs/img_<job>.json = {"scene": ["query", ...], ...})
writes tests/img/<job>/<scene>_<n>.<ext> and tests/img/<job>/credits.json"""
import os, sys, json, re, urllib.parse, urllib.request
UA = 'rpg-edu-bot/1.0 (https://github.com/RPG-ENTERTAINMENT/robokun-voice; rpgentertainment2014@gmail.com)'
OK_LIC = re.compile(r'^(cc0|pdm|public domain|pd|cc by \d(\.\d)?|cc-by-\d(\.\d)?|cc by)$', re.I)
def get(u, t=30): return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=t).read()
def openverse(q):
    u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'license': 'cc0,pdm,by', 'page_size': 12, 'mature': 'false', 'category': 'photograph'})
    out = []
    for r in json.loads(get(u)).get('results', []):
        if (r.get('width') or 0) < 900: continue
        out.append(dict(url=r['url'], src='openverse', credit=f"{r.get('title') or 'photo'} / {r.get('creator') or 'unknown'} ({(r.get('license') or '').upper()} {r.get('license_version') or ''}) {r.get('foreign_landing_url') or ''}".strip()))
    return out
def commons(q):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': f'filetype:bitmap {q}', 'gsrnamespace': 6, 'gsrlimit': 12, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 1400})
    out = []
    for p in sorted(json.loads(get(u)).get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 99)):
        ii = (p.get('imageinfo') or [{}])[0]; md = ii.get('extmetadata', {})
        lic = (md.get('LicenseShortName', {}).get('value') or '').strip()
        if not OK_LIC.match(lic) or 'sa' in lic.lower() or (ii.get('width') or 0) < 900: continue
        artist = re.sub('<[^>]+>', '', md.get('Artist', {}).get('value', '') or 'unknown').strip()[:60]
        out.append(dict(url=ii.get('thumburl') or ii.get('url'), src='commons', credit=f"{p.get('title', '').replace('File:', '')} / {artist} ({lic}) {ii.get('descriptionurl', '')}"))
    return out
job = sys.argv[1]; spec = json.load(open(f'jobs/img_{job}.json'))
od = f'tests/img/{job}'; os.makedirs(od, exist_ok=True); credits = {}
for scene, qs in spec.items():
    n = 0
    for q in qs:
        for src in (openverse, commons):
            try: cands = src(q)
            except Exception as e: print('search fail', scene, q, repr(e)[:100]); continue
            for c in cands[:3]:
                if n >= 6: break
                try:
                    b = get(c['url'], 40)
                    if len(b) < 20000: continue
                    ext = 'png' if b[:4] == b'\x89PNG' else 'jpg'
                    fn = f'{scene}_{n}.{ext}'; open(f'{od}/{fn}', 'wb').write(b); credits[fn] = dict(query=q, **c); n += 1
                    print('ok', fn, q, c['src'])
                except Exception as e: print('dl fail', repr(e)[:100])
json.dump(credits, open(f'{od}/credits.json', 'w'), ensure_ascii=False, indent=1)
print('done', len(credits))
