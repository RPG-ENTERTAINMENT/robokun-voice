"""ポーズ画像をAI（Real-ESRGAN アニメ用）で4倍に高画質化して assets/sprites_hd/ に保存する。
使い方: python3 engine/upscale.py <重みファイル.pth>   （失敗しても動画づくりは普通の画像で続く）"""
import json, os, sys
import numpy as np, torch, spandrel
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'assets')
OUT = os.path.join(A, 'sprites_hd')
torch.set_num_threads(os.cpu_count() or 2)
model = spandrel.ModelLoader().load_from_file(sys.argv[1]).eval()


def run(x):
    t = torch.from_numpy(x).permute(2, 0, 1)[None]
    with torch.no_grad():
        return model(t).clamp(0, 1)[0].permute(1, 2, 0).numpy()


os.makedirs(OUT, exist_ok=True)
atlas = Image.open(os.path.join(A, 'sprites.webp')).convert('RGBA')
pos = json.load(open(os.path.join(A, 'sprites.json')))
pad = 8
for name, (x, y, w, h) in pos.items():
    c = Image.new('RGBA', (w + 2 * pad, h + 2 * pad))
    c.paste(atlas.crop((x, y, x + w, y + h)), (pad, pad))
    a = np.array(c).astype(np.float32) / 255
    rgb = run(np.ascontiguousarray(a[..., :3]))
    al = run(np.ascontiguousarray(np.repeat(a[..., 3:4], 3, 2))).mean(2, keepdims=True)
    im = Image.fromarray((np.concatenate([rgb, al], 2) * 255).round().astype(np.uint8), 'RGBA')
    im.crop((4 * pad, 4 * pad, 4 * pad + 4 * w, 4 * pad + 4 * h)).save(os.path.join(OUT, name + '.png'))
    print('hd', name, flush=True)
