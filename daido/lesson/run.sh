#!/bin/bash
# 大道芸講座（@daidogeisenmon の横動画）: jobs/daily_task = daido:lesson:<episodes>（確認用に作るだけ）/ daido:lessonup:<episodes>（公開アップ）
# called from daido/run.sh with "lesson:1,2" or "lessonup:1,2". Results: daido/state/lessons.json
KIND="${1%%:*}"; EPS="${1#*:}"; [ "$EPS" = "$1" ] && EPS=1
echo "DAIDO LESSON $KIND EPS=$EPS"; mkdir -p daido/logs daido/state
( sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-color-emoji ) > daido/logs/lesson_apt.txt 2>&1
python -m pip install -q numpy pillow google-api-python-client google-auth cryptography > daido/logs/lesson_pip.txt 2>&1
[ -d assets/sp ] || { unzip -q -n robokun_assets.zip -d . ; mkdir -p assets && cp -rn robokun_assets/* assets/; }
G=https://github.com/VOICEVOX
mkdir -p vv
[ -n "$(ls vv/voicevox_onnxruntime*/lib/libvoicevox_onnxruntime.so* 2>/dev/null)" ] || curl -sSL $G/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C vv
[ -d vv/open_jtalk_dic_utf_8-1.11 ] || curl -sSL https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz | tar xz -C vv
[ -f vv/0.vvm ] || curl -sSL -o vv/0.vvm $G/voicevox_vvm/releases/download/0.16.1/0.vvm
curl -sSL -o /tmp/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl $G/voicevox_core/releases/download/0.16.2/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl
python -m pip install -q /tmp/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl >> daido/logs/lesson_pip.txt 2>&1
export VV_DIR=$(pwd)/vv IGC_ASSETS=$(pwd)/assets IGC_SPRITES=$(pwd)/assets/sp IGC_PHOTOS=$(pwd)/tests/img/edu001 DG_WORK=$(pwd)/daido_lesson_work
set -o pipefail
python daido/lesson/build.py $EPS $([ "$KIND" = lessonup ] && echo --upload) 2>&1 | grep -v '^upload ' | tee daido/logs/lesson_build.txt
