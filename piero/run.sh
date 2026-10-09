#!/bin/bash
# piero channel entry point. Called from scripts/daily.sh (daily.yml):
#   bash piero/run.sh <task>     task = daily | test | auth_url | auth_code | ...
TASK="${1:-test}"
echo "PIERO TASK=$TASK"; mkdir -p piero/logs piero/state
( sudo apt-get update -qq && sudo apt-get install -y -qq fonts-noto-cjk fonts-noto-cjk-extra ffmpeg ) > piero/logs/apt.txt 2>&1
python -m pip install -q cryptography numpy scipy pillow pyopenjtalk google-api-python-client google-auth > piero/logs/pip.txt 2>&1
set -o pipefail
case "$TASK" in
  auth_url)  python piero/auth.py url 2>&1 | tee piero/logs/auth.txt ;;
  auth_code) python piero/auth.py code 2>&1 | tee piero/logs/auth.txt; rm -f piero/jobs/auth_code.txt ;;
  auth_keygen) python piero/auth.py keygen 2>&1 | tee piero/logs/auth.txt ;;
  auth_import) python piero/auth.py import 2>&1 | tee piero/logs/auth.txt; rm -f piero/jobs/rt_in.b64 ;;
  *)         python piero/main.py "$TASK" 2>&1 | tee piero/logs/main_$TASK.txt ;;
esac
rc=$?
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = piero ] && echo make > jobs/daily_task
git config user.name piero-bot; git config user.email bot@users.noreply.github.com
for p in piero/state piero/logs piero/jobs piero/rt.enc piero/pub.pem piero/key.enc jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git add -u piero 2>/dev/null
git commit -qm "piero: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
