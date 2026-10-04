#!/bin/bash
# daily landscape episode (render + scheduled upload). args passed to long_daily.py (--test / --now)
bash scripts/setup_all.sh > logs/setup_long.txt 2>&1
source ~/venv/bin/activate
pip install -q google-api-python-client google-auth
cp eng/engine.py eng/engine_l.py && patch -l eng/engine_l.py patches/engine_l.diff && patch -l eng/lib.py patches/lib.diff || exit 1
python scripts/long_daily.py "$@" 2>&1 | tee logs/long_daily.txt
