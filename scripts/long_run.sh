#!/bin/bash
# daily landscape episode (render + scheduled upload). args passed to long_daily.py (--test / --now)
# if it fails (e.g. out of memory), it retries once automatically with fewer render processes.
bash scripts/setup_all.sh > logs/setup_long.txt 2>&1
source ~/venv/bin/activate
pip install -q google-api-python-client google-auth
cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
python scripts/long_daily.py "$@" > logs/long_daily.txt 2>&1
rc=$?
cat logs/long_daily.txt
if [ $rc -ne 0 ]; then
  echo "long_daily failed ($rc) - retrying with 1 render process"
  LONG_PROCS=1 python scripts/long_daily.py "$@" > logs/long_daily_retry.txt 2>&1
  rc=$?; cat logs/long_daily_retry.txt
fi
exit $rc
