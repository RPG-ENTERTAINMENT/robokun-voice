# used by setup.sh: python upscale.py <model_dir> in1 out1 [in2 out2 ...]
# Real-ESRGAN anime x4 (ncnn, CPU) for RGBA sprites: bleed colour into transparent area, upscale RGB with the model, alpha with Lanczos
import sys, numpy as np, ncnn
from PIL import Image, ImageFilter
from scipy import ndimage
MD = sys.argv[1]
net = ncnn.Net(); net.opt.use_vulkan_compute = False; net.opt.num_threads = 4
net.load_param(f'{MD}/realesrgan-x4plus-anime.param'); net.load_model(f'{MD}/realesrgan-x4plus-anime.bin')
def bleed(rgba):
    a = rgba[..., 3] > 8
    idx = ndimage.distance_transform_edt(~a, return_distances=False, return_indices=True)
    out = rgba[..., :3][idx[0], idx[1]]
    return out
def run(tile):
    mat = ncnn.Mat.from_pixels(np.ascontiguousarray(tile), ncnn.Mat.PixelType.PIXEL_RGB, tile.shape[1], tile.shape[0])
    mat.substract_mean_normalize([], [1 / 255.0] * 3)
    ex = net.create_extractor(); ex.input('data', mat); _, o = ex.extract('output')
    return np.array(o).transpose(1, 2, 0)
def run_tiled(img, T=128, O=12):
    # tiles with overlap (keeps memory small); centre of each tile is kept
    h, w = img.shape[:2]; out = np.zeros((h * 4, w * 4, 3), np.float32)
    for y in range(0, h, T):
        for x in range(0, w, T):
            y0, x0 = max(0, y - O), max(0, x - O); y1, x1 = min(h, y + T + O), min(w, x + T + O)
            r = run(img[y0:y1, x0:x1])
            ty1, tx1 = min(h, y + T), min(w, x + T)
            out[y * 4:ty1 * 4, x * 4:tx1 * 4] = r[(y - y0) * 4:(ty1 - y0) * 4, (x - x0) * 4:(tx1 - x0) * 4]
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
def up(path, out):
    im = np.array(Image.open(path).convert('RGBA'))
    P = 12
    im = np.pad(im, ((P, P), (P, P), (0, 0)))
    rgb = bleed(im).astype(np.float32)
    o = run_tiled(rgb.astype(np.uint8))
    al = Image.fromarray(im[..., 3]).resize((o.shape[1], o.shape[0]), Image.LANCZOS)
    al = np.array(al.filter(ImageFilter.GaussianBlur(0.6)))
    res = np.dstack([o, al]); res[al < 3] = 0
    r = Image.fromarray(res); bb = r.getbbox(); r.crop(bb).save(out)
for p, o in zip(sys.argv[2::2], sys.argv[3::2]): up(p, o); print(o)
