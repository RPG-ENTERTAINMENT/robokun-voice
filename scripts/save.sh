#!/bin/bash
# commit state/logs/tests back to the repo (robust: worktree may be dirty from engine patches)
git config user.name robokun-bot
git config user.email bot@users.noreply.github.com
git add state logs tests 2>/dev/null
git commit -m "bot: update [skip ci]" || true
for i in 1 2 3 4 5; do
  git pull --rebase --autostash -X theirs -q && git push && exit 0
  git rebase --abort 2>/dev/null; sleep $((i*5))
done
exit 1
