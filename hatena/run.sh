#!/bin/bash
# あなたのハテナを解決してみる OLゆりとロボしず (@hatenayurirobo). Called from scripts/daily.sh:
#   jobs/daily_task = hatena:<task>, and daily after the 01:40 / 12:30 JST runs.
#   bash hatena/run.sh <task>   task = envtest | auth_url | auth_code | test[:<n>] | daily
TASK="${1:-envtest}"
echo "HATENA TASK=$TASK"; mkdir -p hatena/logs hatena/state hatena/jobs logs
export PATH="$HOME/.local/bin:$PATH"
set -o pipefail
if [ "$TASK" = envtest ]; then
  bash hatena/setup.sh > hatena/logs/setup.txt 2>&1
  ~/hvenv/bin/python hatena/envtest.py > hatena/logs/envtest.txt 2>&1; rc=$?
elif [ -f hatena/main.sh ]; then
  bash hatena/main.sh "$TASK"; rc=$?
else
  echo "hatena: not ready" > hatena/logs/notready.txt; rc=0
fi
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = hatena ] && echo make > jobs/daily_task
git config user.name hatena-bot; git config user.email bot@users.noreply.github.com
for p in hatena/state hatena/logs hatena/jobs hatena/rt.enc hatena/channel_id.txt jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git commit -qm "hatena: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
