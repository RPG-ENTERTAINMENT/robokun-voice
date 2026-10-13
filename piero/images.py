"""Reference photos for each item: search free-licence photo libraries (Openverse, Wikimedia Commons),
then turn them into creepy 'evidence photos'. Only CC0 / public domain / CC BY are used; credits are collected
for the video description. Any failure just returns None (the video is still made, without that photo)."""
import os, io, json, re, hashlib, urllib.parse, urllib.request
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageEnhance

UA = 'piero-channel-bot/1.0 (https://github.com/RPG-ENTERTAINMENT/robokun-voice; rpgentertainment2014@gmail.com)'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'piero_work', 'img')
os.makedirs(CACHE, exist_ok=True)
PEOPLE = re.compile(r'\b(person|people|man|men|woman|women|girl|boy|child|children|kid|kids|baby|babies|toddler|portrait|selfie|face|faces|family|couple|bride|groom|student|students|model|lady|guy|teen|teenager|human|cartoon|anime|manga|character|drawing|illustration|clipart|clip art|vector)\b', re.I)
OK_LIC = re.compile(r'^(cc0|pdm|public domain|pd|cc by \d(\.\d)?|cc-by-\d(\.\d)?|cc by)$', re.I)

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return urllib.request.urlopen(req, timeout=timeout).read()

def _openverse(q):
    u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(
        {'q': q, 'license': 'cc0,pdm,by', 'page_size': 20, 'mature': 'false', 'category': 'photograph,digitized_artwork'})
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

def horror_border(W, H, b=62, seed=0):
    """full-screen RGBA overlay: an old carved, tarnished gilt picture frame around the edges of the video
    (transparent in the middle), with cracks, cobwebs in the top corners and blood running in from the top rail"""
    rng = np.random.default_rng(seed + 21)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
    d = dist / b
    hm = (0.9 * np.exp(-((d - 0.12) / 0.10) ** 2) + 0.55 * np.exp(-((d - 0.82) / 0.09) ** 2) + 0.25 * np.clip(1 - d, 0, 1))
    orn = np.tanh(gaussian_filter(rng.normal(0, 1, (H, W)), 3.2) * 6)
    cx = np.minimum(xx, W - 1 - xx); cy = np.minimum(yy, H - 1 - yy)
    corner = np.exp(-((cx / (b * 2.2)) ** 2 + (cy / (b * 2.2)) ** 2))
    band = np.exp(-((d - 0.47) / 0.17) ** 2)
    hm = gaussian_filter(hm + 0.32 * orn * band * (0.6 + 0.9 * corner) + 0.5 * corner * band, 1.0)
    gy, gx = np.gradient(hm * 40)
    nz = 1.0 / np.sqrt(gx ** 2 + gy ** 2 + 1)
    L = np.array([-0.55, -0.6, 0.58]); L /= np.linalg.norm(L)
    shade = np.clip((-gx * L[0] - gy * L[1] + L[2]) * nz, 0, 1)
    grime = np.clip(0.55 + 0.35 * (gaussian_filter(rng.normal(0, 1, (H, W)), 6) * 3 + gaussian_filter(rng.normal(0, 1, (H, W)), 1.2) * 0.6), 0, 1)
    dark = np.array([34, 22, 11], np.float32); gold = np.array([138, 98, 44], np.float32); hi = np.array([205, 165, 95], np.float32)
    t = np.clip(shade * (0.35 + 0.65 * grime) * (0.6 + 0.6 * hm), 0, 1)[..., None]
    rgb = dark + (gold - dark) * np.clip(t * 1.4, 0, 1) + (hi - gold) * np.clip((t - 0.72) * 3, 0, 1)
    rgb *= (0.35 + 0.65 * grime[..., None])
    alpha = np.where(dist < b, 255.0, 0.0)
    # inner shadow falling onto the video
    inner = np.clip((dist - b) / 55.0, 0, 1)
    sh_a = np.where(dist >= b, (1 - inner) ** 2 * 150, 0)
    alpha = np.maximum(alpha, sh_a)
    rgb = np.where((dist >= b)[..., None], 0, rgb)
    img = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), 'RGBA')
    dr = ImageDraw.Draw(img)
    # cracks in the wood
    for _ in range(16):
        side = rng.integers(4)
        x, y = (rng.uniform(0, W), rng.uniform(0, b)) if side < 2 else (rng.uniform(0, b), rng.uniform(0, H))
        if side == 1: y = H - y
        if side == 3: x = W - x
        pts = [(x, y)]
        for _ in range(10): x += rng.normal(0, 8); y += rng.normal(0, 8); pts.append((x, y))
        dr.line(pts, fill=(8, 4, 2, 255), width=2)
    # cobwebs in the two top corners
    for cx0, sx in ((b - 4, 1), (W - b + 4, -1)):
        R = 170
        for k in range(7):
            ang = np.pi / 2 * k / 6
            dr.line([(cx0, b - 4), (cx0 + sx * R * np.cos(ang), b - 4 + R * np.sin(ang))], fill=(200, 200, 195, 110), width=1)
        for r in range(30, R, 28):
            pts = [(cx0 + sx * r * np.cos(np.pi / 2 * k / 12) * (0.92 + 0.08 * (k % 2)), b - 4 + r * np.sin(np.pi / 2 * k / 12) * (0.92 + 0.08 * (k % 2))) for k in range(13)]
            dr.line(pts, fill=(200, 200, 195, 90), width=1)
    # blood seeping from the top rail down over the picture, and from the side rails
    blood = Image.new('RGBA', (W, H), (0, 0, 0, 0)); db = ImageDraw.Draw(blood)
    for k in range(7):
        x0 = rng.uniform(b, W - b); Ln = rng.uniform(b + 40, b + 260); wd = rng.uniform(6, 13)
        xs = x0 + np.cumsum(rng.normal(0, 0.7, 50)); ys = np.linspace(rng.uniform(4, b * 0.5), Ln, 50)
        for i in range(49): db.line([(xs[i], ys[i]), (xs[i + 1], ys[i + 1])], fill=(62, 0, 0, 255), width=max(2, int(wd * (1 - 0.55 * i / 50))))
        db.ellipse([xs[-1] - wd * 0.6, ys[-1] - wd * 0.3, xs[-1] + wd * 0.6, ys[-1] + wd * 1.1], fill=(62, 0, 0, 255))
    for k in range(4):
        side = rng.integers(2); x0 = b * 0.5 if side == 0 else W - b * 0.5
        y0 = rng.uniform(H * 0.15, H * 0.75); Ln = rng.uniform(80, 220); wd = rng.uniform(5, 9)
        db.line([(x0, y0), (x0 + rng.normal(0, 2), y0 + Ln)], fill=(58, 0, 0, 255), width=int(wd))
        db.ellipse([x0 - wd * 0.6, y0 + Ln - wd * 0.3, x0 + wd * 0.6, y0 + Ln + wd], fill=(58, 0, 0, 255))
    ba = np.asarray(blood).astype(np.float32); al = gaussian_filter(ba[..., 3], 0.8)
    hl = np.clip(-np.gradient(gaussian_filter(al, 2.0), axis=1) * 0.08, 0, 1)
    img.alpha_composite(Image.fromarray(np.clip(np.dstack([62 + 70 * hl, 2 + 14 * hl, 2 + 14 * hl, al * 0.93]), 0, 255).astype(np.uint8), 'RGBA'))
    return img
