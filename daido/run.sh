#!/bin/bash
# 大道芸専門アカデミー channel entry point. Called from scripts/daily.sh (daily.yml): jobs/daily_task = daido:<task>, and daily after the 01:40 / 12:30 JST runs.
#   bash daido/run.sh <task>   task = daily | test[:<id>] | auth_url | auth_code
TASK="${1:-test}"
echo "DAIDO TASK=$TASK"; mkdir -p daido/logs daido/state daido/jobs logs
set -o pipefail
if [ "${TASK%%_*}" = auth ]; then
  python -m pip install -q cryptography > daido/logs/pip.txt 2>&1
  case "$TASK" in
    auth_url)  (cd daido && python auth.py url) 2>&1 | tee daido/logs/auth.txt ;;
    auth_code) (cd daido && python auth.py code) 2>&1 | tee daido/logs/auth.txt; rm -f daido/jobs/auth_code.txt ;;
  esac
  rc=$?
else
  (cd daido && python3 make_eps.py) || exit 1   # ネタ帳 → daido/episodes/*.json + index.json
  bash scripts/setup_all.sh > daido/logs/setup.txt 2>&1
  source ~/venv/bin/activate
  pip install -q google-api-python-client google-auth cryptography >> daido/logs/setup.txt 2>&1
  unzip -o -q robokun_assets.zip 'eng/lib.py' -d .   # fresh lib.py (may already be patched earlier in the same run)
  cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
  python scripts/shorts_tempo.py eng/engine_l.py && python daido/patch_engine.py eng/engine_l.py || exit 1
  python daido/main.py ${TASK/:/ } 2>&1 | tee daido/logs/main_${TASK%%:*}.txt
  rc=$?
fi
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = daido ] && echo make > jobs/daily_task
git config user.name daido-bot; git config user.email bot@users.noreply.github.com
for p in daido/state daido/logs daido/jobs daido/rt.enc daido/channel_id.txt jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git commit -qm "daido: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
