#!/bin/bash
set -x
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg rubberband-cli > /dev/null
ffmpeg -hide_banner -filters 2>/dev/null | grep -q rubberband && echo "rubberband filter OK"
# ---- assets (zip uploaded once; repo files take precedence)
if [ -f robokun_assets.zip ]; then unzip -q -n robokun_assets.zip -d . ; fi
mkdir -p assets && cp -rn robokun_assets/* assets/ 2>/dev/null
if [ -f pets_assets.zip ]; then unzip -q -n pets_assets.zip -d . ; cp -rn pets_assets/* assets/ 2>/dev/null; fi
python3 scripts/patches.py
# ---- python deps (venv cached by workflow)
export PIP_NO_CACHE_DIR=1
# The cached venv breaks when the runner's Python patch version changes (its python symlink
# points at the old toolcache path). Check that it really works, not just that the marker exists.
if [ ! -f ~/venv/ok ] || ! ~/venv/bin/python -c "import PIL, soundfile, torch, librosa" 2>/dev/null; then
  echo "venv missing or broken -> rebuilding"
  rm -rf ~/venv
  python -m venv ~/venv; source ~/venv/bin/activate
  pip install -q torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  [ -d gsv ] || git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git gsv
  printf "torch==2.6.0+cpu\ntorchaudio==2.6.0+cpu\n" > /tmp/cons.txt
  pip install -q -r gsv/requirements.txt -c /tmp/cons.txt --extra-index-url https://download.pytorch.org/whl/cpu || true
  pip install -q huggingface_hub soundfile librosa opencv-python-headless pillow numpy fonttools
  pip install -q https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.2/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl
  touch ~/venv/ok
fi
source ~/venv/bin/activate
python - <<'PY'
import glob, os, subprocess
from PIL import Image
for f in glob.glob('assets/**/*.webp', recursive=True):
    Image.open(f).save(f[:-5]+'.png')
for f in glob.glob('assets/audio/**/*.ogg', recursive=True):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f,'-ar','48000',f[:-4]+'.wav'],check=True)
print('assets ready')
PY
[ -d gsv ] || git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git gsv
[ -f gsv/GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth ] || (cd gsv && python -c "from huggingface_hub import snapshot_download; snapshot_download('lj1995/GPT-SoVITS', local_dir='GPT_SoVITS/pretrained_models', allow_patterns=['gsv-v2final-pretrained/*','chinese-hubert-base/*','chinese-roberta-wwm-ext-large/*'])")
mkdir -p gsv/GPT_SoVITS/pretrained_models/fast_langdetect
# ---- VOICEVOX
mkdir -p vv; cd vv
G=https://github.com/VOICEVOX
[ -d voicevox_onnxruntime-linux-x64-1.17.3 ] || (curl -sSL -o o.tgz $G/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz && tar xzf o.tgz && rm o.tgz)
[ -d open_jtalk_dic_utf_8-1.11 ] || (curl -sSL -o d.tgz https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz && tar xzf d.tgz && rm d.tgz)
for i in 0 6 9 13; do [ -f $i.vvm ] || curl -sSL -o $i.vvm $G/voicevox_vvm/releases/download/0.16.1/$i.vvm; done
cd ..
# ---- reference voice clips
python scripts/prep.py
