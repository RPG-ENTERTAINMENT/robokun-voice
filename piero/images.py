"""Reference photos for each item: search free-licence photo libraries (Openverse, Wikimedia Commons),
then turn them into creepy 'evidence photos'. Only CC0 / public domain / CC BY are used; credits are collected
for the video description. Any failure just returns None (the video is still made, without that photo)."""
import os, io, json, re, hashlib, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance

UA = 'piero-channel-bot/1.0 (https://github.com/RPG-ENTERTAINMENT/robokun-voice; rpgentertainment2014@gmail.com)'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'piero_work', 'img')
os.makedirs(CACHE, exist_ok=True)
PEOPLE = re.compile(r'\b(person|people|man|men|woman|women|girl|boy|child|children|kid|kids|baby|babies|toddler|portrait|selfie|face|faces|family|couple|bride|groom|student|students|model|lady|guy|teen|teenager|human)\b', re.I)
OK_LIC = re.compile(r'^(cc0|pdm|public domain|pd|cc by \d(\.\d)?|cc-by-\d(\.\d)?|cc by)$', re.I)

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return urllib.request.urlopen(req, timeout=timeout).read()

def _openverse(q):
    u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(
        {'q': q, 'license': 'cc0,pdm,by', 'page_size': 20, 'mature': 'false', 'category': 'photograph,illustration,digitized_artwork'})
    out = []
    for r in json.loads(_get(u)).get('results', []):
        w, h = r.get('width') or 0, r.get('height') or 0
        if w and w < 700: continue
        words = ' '.join([r.get('title') or ''] + [t.get('name', '') for t in (r.get('tags') or [])])
        if PEOPLE.search(words): continue      # no photos of (real) people
        out.append(dict(url=r['url'], w=w, h=h, credit=f"{r.get('title') or 'photo'} / {r.get('creator') or 'unknown'} ({(r.get('license') or '').upper()} {r.get('license_version') or ''}) {r.get('foreign_landing_url') or ''}".strip()))
    return out

def _commons(q):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': f'filetype:bitmap {q}', 'gsrnamespace': 6,
        'gsrlimit': 20, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 1400})
    pages = json.loads(_get(u)).get('query', {}).get('pages', {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get('index', 99)):
        ii = (p.get('imageinfo') or [{}])[0]; md = ii.get('extmetadata', {})
        lic = (md.get('LicenseShortName', {}).get('value') or '').strip()
        if not OK_LIC.match(lic) or 'sa' in lic.lower(): continue
        if (ii.get('width') or 0) < 700: continue
        desc = re.sub('<[^>]+>', ' ', md.get('ImageDescription', {}).get('value', '') or '')
        if PEOPLE.search(p.get('title', '') + ' ' + desc + ' ' + (md.get('Categories', {}).get('value') or '')): continue
        artist = re.sub('<[^>]+>', '', md.get('Artist', {}).get('value', '') or 'unknown').strip()[:60]
        out.append(dict(url=ii.get('thumburl') or ii.get('url'), w=ii.get('width'), h=ii.get('height'),
                        credit=f"{p.get('title', '').replace('File:', '')} / {artist} ({lic}) {ii.get('descriptionurl', '')}"))
    return out

def fetch(queries, seed=0, used=None):
    """try each query on each source; return (PIL.Image RGB, credit) or (None, None)"""
    used = used if used is not None else set()
    for q in queries:
        for src in (_openverse, _commons):
            key = hashlib.md5(f'{src.__name__}:{q}'.encode()).hexdigest()
            meta = os.path.join(CACHE, key + '.json')
            try:
                cands = json.load(open(meta)) if os.path.exists(meta) else src(q)
                json.dump(cands, open(meta, 'w'))
            except Exception as e:
                print('image search failed', src.__name__, q, repr(e)[:120]); continue
            cands = [c for c in cands if c['url'] not in used]
            if not cands: continue
            # keep the search engine's relevance order; only drop very tall / very wide pictures
            ratio = lambda c: (c['w'] or 3) / max(1, c['h'] or 2)
            cands = [c for c in cands if 0.95 <= ratio(c) <= 2.4] or cands
            for c in cands:
                f = os.path.join(CACHE, hashlib.md5(c['url'].encode()).hexdigest() + '.img')
                try:
                    if not os.path.exists(f): open(f, 'wb').write(_get(c['url'], 40))
                    im = Image.open(f).convert('RGB')
                    if im.width < 500: continue
                    used.add(c['url'])
                    return im, c['credit']
                except Exception as e:
                    print('image download failed', repr(e)[:120])
    return None, None

# ------------------------------------------------------------------ looks
def _fit(im, w, h):
    return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.45))

def creepy(im, w, h, seed=0, tint=(1.0, 0.86, 0.78)):
    """dark, slightly desaturated, red-cold toned, grainy, vignetted photo"""
    im = _fit(im, w, h)
    im = ImageEnhance.Color(im).enhance(0.45)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    a = np.asarray(im).astype(np.float32) / 255
    a = a ** 1.25 * np.array(tint, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = np.clip(1.15 - 0.85 * (((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2), 0.15, 1)
    rng = np.random.default_rng(seed)
    a = a * vig[..., None] + rng.normal(0, 0.035, (h, w, 1)).astype(np.float32)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(5):   # film scratches
        x = int(rng.uniform(0, w)); d.line([x, 0, x + int(rng.uniform(-20, 20)), h], fill=(200, 190, 175), width=1)
    return img

def evidence_card(im, w, h, seed=0, label=None, font=None):
    """the photo as a slightly tilted old print with a border, tape and drop shadow (RGBA)"""
    ph = creepy(im, w, h, seed)
    b = max(10, w // 40)
    card = Image.new('RGBA', (w + 2 * b, h + 2 * b + (b * 3 if label else 0)), (226, 218, 200, 255))
    card.paste(ph, (b, b))
    if label and font:
        d = ImageDraw.Draw(card); tw = d.textlength(label, font=font)
        d.text(((card.width - tw) / 2, h + b + b * 0.6), label, font=font, fill=(120, 10, 10))
    # aged edges
    a = np.asarray(card).astype(np.float32)
    rng = np.random.default_rng(seed + 1)
    stain = rng.normal(0, 1, (card.height // 8 + 1, card.width // 8 + 1))
    stain = np.kron(stain, np.ones((8, 8)))[:card.height, :card.width]
    a[..., :3] *= (0.92 + 0.05 * np.clip(stain, -1, 1))[..., None]
    card = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(card)
    tape = (205, 195, 160, 190)
    d.polygon([(card.width * 0.42, -8), (card.width * 0.58, -8), (card.width * 0.6, b * 2.2), (card.width * 0.4, b * 2.2)], fill=tape)
    ang = [-3.5, 2.5, -2, 3, -1.5][seed % 5]
    card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
    sh = Image.new('RGBA', (card.width + 60, card.height + 60), (0, 0, 0, 0))
    m = card.split()[3].point(lambda v: int(v * 0.75))
    sh.paste((0, 0, 0, 255), (40, 44), m)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    sh.alpha_composite(card, (30, 30))
    return sh

def background(im, w, h, seed=0):
    """full-bleed darkened photo for thumbnails"""
    ph = creepy(im, w, h, seed, tint=(1.0, 0.7, 0.65))
    ph = ImageEnhance.Brightness(ph).enhance(0.8)
    return ph
