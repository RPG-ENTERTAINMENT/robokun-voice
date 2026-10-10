#!/bin/bash
# heavy setup for rendering (ffmpeg, python libs, assets, fonts, VOICEVOX). Run from aika/.
( sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg ) > logs/apt.txt 2>&1
python -m pip install -q numpy scipy pillow cryptography google-api-python-client google-auth > logs/pip.txt 2>&1
# assets (sprites + backgrounds) are stored as base64 chunks
if [ ! -d assets ]; then cat assets_b64/p_* | base64 -d | tar xz; fi
# sharper character sprites: Real-ESRGAN anime x4 (ncnn, CPU) -> assets_hd/*.png (render.py uses them when present)
if [ ! -d assets_hd ]; then
  python -m pip install -q ncnn >> logs/pip.txt 2>&1
  curl -sSL -o /tmp/rr.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip \
    && mkdir -p /tmp/rrm && unzip -q -o -j /tmp/rr.zip '*realesrgan-x4plus-anime.*' -d /tmp/rrm
  mkdir -p assets_hd
  for f in assets/b*_[0-9][0-9].webp; do echo "$f assets_hd/$(basename "$f" .webp).png"; done \
    | xargs -n 22 python upscale.py /tmp/rrm > logs/upscale.txt 2>&1 || { echo 'upscale failed, using normal sprites'; rm -rf assets_hd; }
fi
# fonts
if [ ! -d fonts/package ]; then mkdir -p fonts && (cd fonts && npm pack -q @expo-google-fonts/m-plus-rounded-1c@0.4.4 >/dev/null && tar xzf *.tgz); fi
# VOICEVOX core 0.17 + models
if [ ! -f vv/models/s0.vvm ]; then
  mkdir -p vv/models vv/onnxruntime && R=https://github.com/VOICEVOX
  curl -sSL -o vv/core.whl $R/voicevox_core/releases/download/0.17.0/voicevox_core-0.17.0-cp310-abi3-manylinux_2_34_x86_64.whl
  curl -sSL $R/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C vv
  cp -a vv/voicevox_onnxruntime-linux-x64-1.17.3/lib/* vv/onnxruntime/
  curl -sSL https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz | tar xz -C vv && mv vv/open_jtalk_dic_utf_8-1.11 vv/dict
  curl -sSL -o vv/models/0.vvm $R/voicevox_vvm/releases/download/0.16.0/0.vvm
  curl -sSL -o vv/models/s0.vvm $R/voicevox_vvm/releases/download/0.16.0/s0.vvm
fi
cp vv/core.whl /tmp/voicevox_core-0.17.0-cp310-abi3-manylinux_2_34_x86_64.whl
python -m pip install -q /tmp/voicevox_core-0.17.0-cp310-abi3-manylinux_2_34_x86_64.whl >> logs/pip.txt 2>&1
export VV_DIR=$(pwd)/vv
