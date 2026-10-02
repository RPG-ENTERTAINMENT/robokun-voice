#!/bin/bash
git config user.name robokun-bot
git config user.email bot@users.noreply.github.com
git add state logs tests 2>/dev/null
git commit -m "bot: update [skip ci]" || true
git pull --rebase -q || true
git push
