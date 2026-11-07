#!/bin/bash
# CRAZY NINJA SHIZUKU channel (@crazyninjajapan) entry point. Called from scripts/daily.sh (daily.yml): jobs/daily_task = ninja:<task>, and daily after the 01:40 / 12:30 JST runs.
#   bash ninja/run.sh <task>   task = daily | test[:<n>] | auth_url | auth_code
TASK="${1:-test}"
echo "NINJA TASK=$TASK"; mkdir -p ninja/logs ninja/state ninja/jobs logs
set -o pipefail
if [ "${TASK%%_*}" = auth ]; then
  python -m pip install -q cryptography > ninja/logs/pip.txt 2>&1
  case "$TASK" in
    auth_url)  (cd ninja && python auth.py url) 2>&1 | tee ninja/logs/auth.txt ;;
    auth_code) (cd ninja && python auth.py code) 2>&1 | tee ninja/logs/auth.txt; rm -f ninja/jobs/auth_code.txt ;;
  esac
  rc=$?
else
  command -v ffmpeg >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg > /dev/null; }
  python -m pip install -q numpy pillow qrcode cryptography google-api-python-client google-auth > ninja/logs/pip.txt 2>&1
  A=ninja/assets
  cat $A/sprites.webp.b64.* | base64 -d > $A/sprites.webp   # 使うポーズを1枚にまとめた画像（テキストに分けて保存してある）
  [ -e $A/media.tar.b64.10 ] && { cat $A/media.tar.b64.* | base64 -d | tar xf - -C $A || rm -f $A/real.mp4 $A/poster.webp $A/logo.webp; }   # 本物のお店の映像・ポスター・ロゴ（全部そろっている時だけ）
  G=https://raw.githubusercontent.com/google/fonts/main
  [ -s $A/LuckiestGuy.ttf ] || curl -fsSL -o $A/LuckiestGuy.ttf $G/apache/luckiestguy/LuckiestGuy-Regular.ttf
  [ -s $A/Poppins-Bold.ttf ] || curl -fsSL -o $A/Poppins-Bold.ttf $G/ofl/poppins/Poppins-Bold.ttf
  F=$(fc-list 2>/dev/null | grep -m1 -o '/[^:]*DejaVuSans-Bold.ttf'); [ -z "$F" ] && { sudo apt-get install -y -qq fonts-dejavu-core > /dev/null; F=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf; }
  cp "$F" $A/DejaVuSans-Bold.ttf
  python ninja/main.py ${TASK/:/ } 2>&1 | tee ninja/logs/main_${TASK%%:*}.txt
  rc=$?
fi
# put the trigger file back so later pushes run robokun's normal task
[ "$(head -1 jobs/daily_task 2>/dev/null | cut -d: -f1)" = ninja ] && echo make > jobs/daily_task
git config user.name ninja-bot; git config user.email bot@users.noreply.github.com
for p in ninja/state ninja/logs ninja/jobs ninja/rt.enc ninja/channel_id.txt jobs/daily_task; do [ -e "$p" ] && git add -A "$p"; done
git commit -qm "ninja: $TASK [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
