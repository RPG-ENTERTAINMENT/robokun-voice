import time, os, sys, json, base64, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out = {}
import bpy
out['bpy'] = bpy.app.version_string
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.mesh.primitive_cube_add()
cam = bpy.data.objects.new('C', bpy.data.cameras.new('C')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -6, 1); cam.rotation_euler = (1.45, 0, 0)
sun = bpy.data.objects.new('S', bpy.data.lights.new('S', 'SUN')); sc.collection.objects.link(sun)
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 2
sc.render.resolution_x, sc.render.resolution_y = 720, 1000
sc.render.filepath = '/tmp/envtest.png'
for i in range(3):
    t1 = time.time()
    try:
        bpy.ops.render.render(write_still=True); out[f'eevee{i}'] = round(time.time() - t1, 2)
    except Exception as e:
        out['eevee_err'] = str(e); break
out['png'] = os.path.exists('/tmp/envtest.png')
out['cpus'] = os.cpu_count()
try:
    from secret import tts_key
    k = tts_key()
    body = {"input": {"text": "テスト"}, "voice": {"languageCode": "ja-JP", "name": "ja-JP-Chirp3-HD-Leda"}, "audioConfig": {"audioEncoding": "LINEAR16"}}
    r = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + k, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    out['tts_bytes'] = len(base64.b64decode(json.load(urllib.request.urlopen(r))['audioContent']))
except Exception as e:
    out['tts_err'] = str(e)[:300]
print(json.dumps(out))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/env.json'), 'w').write(json.dumps(out, ensure_ascii=False, indent=1))
