#!/bin/bash
# Re-upload the lesson videos (インスタ講座 igc / オーディション講座 aud / アイドル講座 idl) to the
# スゴ技スクールRPG東京校 channel (@sugowazaschool) instead of ロボしず.
#   jobs/daily_task = tosugo:<list>   e.g. tosugo:igc,aud,idl
# The old ロボしず ids are kept in <x>/state/videos_robo.json; new ids go to <x>/state/videos.json.
LIST="${1:-igc,aud,idl}"
python -m pip install -q cryptography > /dev/null 2>&1
export YT_REFRESH_TOKEN=$(python3 - <<'P'
import os, base64, hashlib
from cryptography.fernet import Fernet
f = Fernet(base64.urlsafe_b64encode(hashlib.sha256(os.environ['YT_CLIENT_SECRET'].encode()).digest()))
print(f.decrypt(open('sugo/rt.enc', 'rb').read()).decode())
P
)
[ -n "$YT_REFRESH_TOKEN" ] || { echo "no sugo token"; exit 1; }
echo "::add-mask::$YT_REFRESH_TOKEN"
rc=0
for x in ${LIST//,/ }; do
  case $x in igc) EPS=1-20;; aud) EPS=1-10;; idl) EPS=1-10;; *) continue;; esac
  if [ -f $x/state/videos.json ] && [ ! -f $x/state/videos_robo.json ]; then
    mv $x/state/videos.json $x/state/videos_robo.json
    git add -A $x/state; git -c user.name=sugo-bot -c user.email=bot@users.noreply.github.com commit -qm "$x: keep ロボしず ids [skip ci]" || true
  fi
  echo "=== $x $EPS -> sugowazaschool"
  bash $x/run.sh $EPS || rc=1
done
echo make > jobs/daily_task
git add jobs/daily_task; git -c user.name=sugo-bot -c user.email=bot@users.noreply.github.com commit -qm "tosugo done [skip ci]" || true
for i in 1 2 3 4 5; do git pull -q --rebase --autostash && git push -q && break; git rebase --abort 2>/dev/null; sleep $((i*5)); done
exit $rc
