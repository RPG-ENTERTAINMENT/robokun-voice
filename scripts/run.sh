#!/bin/bash
set -x
mkdir -p logs out
exec > >(tee logs/run.txt) 2>&1
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg > /dev/null
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL || true
df -h /; nproc; free -g
git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git gsv
(cd gsv && git log -1 --format=%H) > logs/gsv_commit.txt
export PIP_NO_CACHE_DIR=1
pip install -q torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3
printf "torch==2.5.1+cpu\ntorchaudio==2.5.1+cpu\n" > /tmp/cons.txt
pip install -q -r gsv/requirements.txt -c /tmp/cons.txt --extra-index-url https://download.pytorch.org/whl/cpu > logs/pip.txt 2>&1 || tail -40 logs/pip.txt
pip install -q huggingface_hub soundfile librosa
python -c "import torch,torchaudio;print(torch.__version__,torchaudio.__version__)"
df -h /
(cd gsv && python -c "from huggingface_hub import snapshot_download; snapshot_download('lj1995/GPT-SoVITS', local_dir='GPT_SoVITS/pretrained_models', allow_patterns=['gsv-v2final-pretrained/*','chinese-hubert-base/*','chinese-roberta-wwm-ext-large/*'])" && ls -R GPT_SoVITS/pretrained_models > ../logs/models.txt)
python scripts/prep.py
cd gsv && python ../scripts/infer.py
