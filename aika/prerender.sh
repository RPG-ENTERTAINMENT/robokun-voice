#!/bin/bash
# OLあいか: render upcoming episodes in the voice queue (voice.yml), separate from the other channels' daily queue.
# Each finished mp4 is pushed to the aika-out branch; aika/run.sh (daily queue) then only uploads it.
cd "$(dirname "$0")"; mkdir -p logs
source setup.sh
git fetch -q --depth=1 origin +aika-out:refs/remotes/origin/aika-out 2>/dev/null || true
python main.py prerender 2>&1 | tee logs/prerender.txt
mkdir -p ../logs && cp logs/prerender.txt ../logs/aika_prerender.txt   # saved to main by scripts/save.sh
