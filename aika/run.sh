#!/bin/bash
# OLあいか channel entry point. Called from scripts/daily.sh (daily.yml):
#   bash aika/run.sh <task>     task = daily | now:<n> | smoke | auth_url | auth_code | render:<ep>
# Rendering normally happens beforehand in the voice queue (aika/prerender.sh), so this only uploads.
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
  python -m pip install -q cryptography google-api-python-client google-auth > logs/pip.txt 2>&1
  # rendering happens in the voice queue (aika/prerender.sh); here we normally only upload the prebuilt mp4s
  git fetch -q --depth=1 origin +aika-out:refs/remotes/origin/aika-out 2>/dev/null || true
  NEED=1; case "$TASK" in daily|now*) NEED=$(python main.py need ${TASK/:/ } 2>/dev/null | tail -1); NEED=${NEED:-1};; esac
  if [ "$NEED" != 0 ] && [ "${TASK%%:*}" = now ]; then echo "now: videos not prebuilt yet — will post on a later run"; exit 0; fi
  if [ "$NEED" != 0 ]; then source setup.sh; fi
  python main.py ${TASK/:/ } 2>&1 | tee logs/main_${TASK%%:*}.txt
  rc=$?
  [ $rc = 0 ] && [ "${TASK%%:*}" = now ] && echo "done $TASK" > jobs/task
fi
cd ..
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = aika ] && echo make > jobs/daily_task
git config user.name aika-bot; git config user.email bot@users.noreply.github.com
for p in aika/state aika/logs aika/jobs aika/rt.enc jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git commit -qm "aika: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
