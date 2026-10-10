#!/bin/bash
# OLあいか channel entry point. Called from scripts/daily.sh (daily.yml):
#   bash aika/run.sh <task>     task = daily | smoke | auth_url | auth_code | render:<ep>
TASK="${1:-smoke}"
cd "$(dirname "$0")"
echo "AIKA TASK=$TASK"; mkdir -p logs state jobs
set -o pipefail
if [ "${TASK%%_*}" = auth ]; then
  python -m pip install -q cryptography > logs/pip.txt 2>&1
  case "$TASK" in
    auth_url)  python auth.py url 2>&1 | tee logs/auth.txt ;;
    auth_code) python auth.py code 2>&1 | tee logs/auth.txt; rm -f jobs/auth_code.txt ;;
  esac
  rc=$?
else
  ( sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg ) > logs/apt.txt 2>&1
  python -m pip install -q numpy scipy pillow cryptography google-api-python-client google-auth > logs/pip.txt 2>&1
  # assets (sprites + backgrounds) are stored as base64 chunks
  if [ ! -d assets ]; then cat assets_b64/part_* | base64 -d | tar x; fi
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
  python main.py ${TASK/:/ } 2>&1 | tee logs/main_${TASK%%:*}.txt
  rc=$?
fi
cd ..
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = aika ] && echo make > jobs/daily_task
git config user.name aika-bot; git config user.email bot@users.noreply.github.com
for p in aika/state aika/logs aika/jobs aika/rt.enc jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git commit -qm "aika: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
