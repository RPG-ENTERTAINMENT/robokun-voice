#!/bin/bash
# legacy zero-shot voice test (voice.yml). Runs only when jobs/RUN_VOICE exists.
mkdir -p logs out
# OLあいか: render upcoming episodes here (own queue, does not wait for / slow down the other channels; HD sprites)
[ -f aika/prerender.sh ] && { bash aika/prerender.sh || true; }
if [ ! -f jobs/RUN_VOICE ]; then echo "skip voice test"; exit 0; fi
set -x
exec > >(tee logs/run.txt) 2>&1
bash scripts/setup_all.sh
source ~/venv/bin/activate
cd gsv && python ../scripts/infer.py
