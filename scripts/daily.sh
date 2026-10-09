#!/bin/bash
# entry point for .github/workflows/daily.yml
SCHED="$1"; TASK="$2"
case "$SCHED" in
  "0 16 * * *"|"40 16 * * *") TASK=make;;
  "0 3 * * *"|"30 3 * * *") TASK=postA;;
  "0 10 * * *"|"30 10 * * *") TASK=postB;;
esac
[ -z "$TASK" ] && [ -f jobs/daily_task ] && TASK=$(head -1 jobs/daily_task | tr -d " \r")
[ -z "$TASK" ] && TASK=test
# --- piero channel (ピエロ君のやばい噂、知識): on-demand tasks via jobs/daily_task = piero:<task>
if [ "${TASK%%:*}" = piero ]; then bash piero/run.sh "${TASK#piero:}"; exit $?; fi
echo "TASK=$TASK"
mkdir -p logs
set -o pipefail
if [ "${TASK%%:*}" = ttauth ]; then
  pip install -q requests
  python scripts/tiktok.py auth "${TASK#ttauth:}" 2>&1 | tee logs/ttauth.txt
elif [ "${TASK%%:*}" = longvoice ]; then
  EP=${TASK#longvoice:}
  bash scripts/setup_all.sh 2>&1 | tee logs/setup.txt
  source ~/venv/bin/activate
  python scripts/robo_tts.py $EP 2>&1 | tee logs/longvoice.txt
  tar czf $EP-vo.tgz $(ls vo/$EP/*.wav | grep -v _raw)
  mkdir -p tests && cp $EP-vo.tgz tests/
  gh release delete $EP-vo -y --cleanup-tag || true
  gh release create $EP-vo $EP-vo.tgz --title "$EP voice" --notes robo --prerelease
elif [ "${TASK%%:*}" = longpost ]; then
  EP=${TASK#longpost:}
  bash scripts/setup_all.sh 2>&1 | tee logs/setup.txt
  source ~/venv/bin/activate
  pip install -q google-api-python-client google-auth
  tar xzf tests/$EP-vo.tgz
  python eng/tts_vv.py episodes/$EP.json vo/$EP --vv vv --skip-robo
  cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
  mkdir -p out
  export ROBO_ASSETS=$(pwd)/assets/ ROBO_ASPECT=16x9
  python eng/engine_l.py episodes/$EP.json vo/$EP out/$EP.mp4 --procs $(nproc) 2>&1 | tee logs/longpost.txt
  ffprobe -v error -show_entries format=duration -of csv=p=0 out/$EP.mp4 | tee -a logs/longpost.txt
  python scripts/long_thumb.py episodes/$EP.json vo/$EP out/$EP.png 2>&1 | tee -a logs/longpost.txt
  python scripts/post_long.py out/$EP.mp4 out/$EP.png config/$EP.yt.json 2>&1 | tee -a logs/longpost.txt
elif [ "${TASK%%:*}" = longthumb ]; then
  R=${TASK#longthumb:}; EP=${R%%:*}; VID=${R#*:}
  bash scripts/setup_all.sh 2>&1 | tee logs/setup.txt
  source ~/venv/bin/activate
  pip install -q google-api-python-client google-auth
  tar xzf tests/$EP-vo.tgz
  python eng/tts_vv.py episodes/$EP.json vo/$EP --vv vv --skip-robo
  cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
  mkdir -p out
  export ROBO_ASSETS=$(pwd)/assets/ ROBO_ASPECT=16x9
  python scripts/long_thumb.py episodes/$EP.json vo/$EP out/$EP.png 2>&1 | tee logs/longthumb.txt
  python scripts/set_thumb.py $VID out/$EP.png 2>&1 | tee -a logs/longthumb.txt
elif [ "$TASK" = longtest ]; then
  bash scripts/long_run.sh --test
elif [ "$TASK" = longnow ]; then
  bash scripts/long_run.sh --now
elif [ "$TASK" = make ] || [ "$TASK" = test ]; then
  bash scripts/setup_all.sh 2>&1 | tee logs/setup.txt
  source ~/venv/bin/activate
  cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
  python scripts/shorts_tempo.py eng/engine_l.py
  python scripts/make_day.py $([ "$TASK" = test ] && echo --test) 2>&1 | tee logs/make.txt
else
  [ -f robokun_assets.zip ] && unzip -q -n robokun_assets.zip 'episodes/*' -d .
  pip install -q google-api-python-client google-auth requests
  # catch-up: if the 12:00 short was missed, post it before the 19:00 one (already-posted slots are skipped)
  if [ "$TASK" = postB ]; then python scripts/post.py --slot A 2>&1 | tee logs/post_catchupA.txt; fi
  python scripts/post.py --slot ${TASK#post} 2>&1 | tee logs/post_${TASK}.txt
  bash scripts/save.sh   # save posted state right away
  # daily landscape episode (skips itself if today's is already uploaded)
  bash scripts/long_run.sh
fi
rc=$?
# --- piero channel: render today's 3 videos and schedule them (12:00 / 16:00 / 20:00 JST). 12:30 run = retry if missed.
case "$SCHED" in "40 16 * * *"|"30 3 * * *") bash piero/run.sh daily || true;; esac
exit $rc
