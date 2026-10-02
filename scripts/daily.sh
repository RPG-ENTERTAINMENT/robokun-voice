#!/bin/bash
# entry point for .github/workflows/daily.yml
SCHED="$1"; TASK="$2"
case "$SCHED" in
  "0 16 * * *") TASK=make;;
  "0 3 * * *") TASK=postA;;
  "0 10 * * *") TASK=postB;;
esac
[ -z "$TASK" ] && TASK=make
echo "TASK=$TASK"
mkdir -p logs
set -o pipefail
if [ "$TASK" = make ] || [ "$TASK" = test ]; then
  bash scripts/setup_all.sh 2>&1 | tee logs/setup.txt
  source ~/venv/bin/activate
  python scripts/make_day.py $([ "$TASK" = test ] && echo --test) 2>&1 | tee logs/make.txt
else
  [ -f robokun_assets.zip ] && unzip -q -n robokun_assets.zip 'episodes/*' -d .
  pip install -q google-api-python-client google-auth requests
  python scripts/post.py --slot ${TASK#post} 2>&1 | tee logs/post_${TASK}.txt
fi
