#!/bin/bash
# オーディション講座（タイムオーディション有料プラン会員向け）: jobs/daily_task = aud:<episodes>  e.g. aud:2
# builds the lesson videos (VOICEVOX ずんだもん) and uploads them to YouTube as unlisted. Results: aud/state/videos.json
EPS="${1:-1}"
echo "AUD EPS=$EPS"; mkdir -p logs aud/state
( sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-color-emoji ) > logs/igc_apt.txt 2>&1
python -m pip install -q numpy pillow google-api-python-client google-auth > logs/igc_pip.txt 2>&1
[ -d assets/sp ] || { unzip -q -n robokun_assets.zip -d . ; mkdir -p assets && cp -rn robokun_assets/* assets/; }
G=https://github.com/VOICEVOX
mkdir -p vv
[ -n "$(ls vv/voicevox_onnxruntime*/lib/libvoicevox_onnxruntime.so* 2>/dev/null)" ] || curl -sSL $G/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C vv
[ -d vv/open_jtalk_dic_utf_8-1.11 ] || curl -sSL https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz | tar xz -C vv
[ -f vv/0.vvm ] || curl -sSL -o vv/0.vvm $G/voicevox_vvm/releases/download/0.16.1/0.vvm
curl -sSL -o /tmp/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl $G/voicevox_core/releases/download/0.16.2/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl
python -m pip install -q /tmp/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl >> logs/igc_pip.txt 2>&1
export VV_DIR=$(pwd)/vv IGC_ASSETS=$(pwd)/assets IGC_SPRITES=$(pwd)/assets/sp IGC_PHOTOS=$(pwd)/tests/img/edu001 AUD_WORK=$(pwd)/aud_work
set -o pipefail
python aud/build.py $EPS --upload ${AUD_PREVIEW:+--preview} 2>&1 | grep -v '^upload ' | tee logs/aud_build.txt
rc=$?
case "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" in aud|audp) echo make > jobs/daily_task;; esac
git config user.name aud-bot; git config user.email bot@users.noreply.github.com
git add aud/state logs/aud_build.txt jobs/daily_task 2>/dev/null
git commit -qm "aud: $EPS [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
