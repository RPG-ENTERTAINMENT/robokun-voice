#!/bin/bash
# called by hatena/run.sh:  bash hatena/main.sh <task>   task = auth_url | auth_code | test[:<n>] | daily
TASK="$1"
export PATH="$HOME/.local/bin:$PATH"
set -o pipefail
if [ "${TASK%%_*}" = auth ]; then
  python3 -m pip install -q cryptography > hatena/logs/pip.txt 2>&1
  case "$TASK" in
    auth_url)  (cd hatena && python3 auth.py url) 2>&1 | tee hatena/logs/auth.txt ;;
    auth_code) (cd hatena && python3 auth.py code) 2>&1 | tee hatena/logs/auth.txt; rm -f hatena/jobs/auth_code.txt ;;
  esac
  exit $?
fi
if [ "$TASK" = daily ] && [ ! -f hatena/rt.enc ]; then echo "YouTube not connected yet - skipping" | tee hatena/logs/main_daily.txt; exit 0; fi
bash hatena/setup.sh > hatena/logs/setup.txt 2>&1
~/hvenv/bin/python hatena/main.py ${TASK/:/ } 2>&1 | tee hatena/logs/main_${TASK%%:*}.txt
