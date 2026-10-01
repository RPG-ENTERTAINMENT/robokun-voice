#!/bin/bash
git config user.name robokun-bot
git config user.email bot@users.noreply.github.com
git add out logs
git commit -m "results [skip ci]" || true
git pull --rebase -q || true
git push
