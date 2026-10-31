# daido — 大道芸専門アカデミー（YouTube @daidogeisenmon）ロボしず大道芸ショート

毎日2本（12:00 / 20:00 JST 予約公開）。ロボしずとハナの大道芸ショートアニメ（ロボしずの声＝本人、ハナ・ナレーション＝VOICEVOX）。
描画はロボしずと同じエンジン（eng/engine_l.py）に `patch_engine.py` で大道芸の演出（juggle / juggle_fail / balloon / coins / spot）と「大道芸専門アカデミー 生徒募集中」の帯を足している。

- ネタ帳: `make_eps.py`（実行のたびに episodes/*.json を生成）、順番は `index.json`。state/state.json の next で順に回る。
- 実行: `scripts/daily.sh` の 01:40 JST の実行後（失敗時の再試行 12:30 JST）に `bash daido/run.sh daily`。手動は `jobs/daily_task` に `daido:test` / `daido:test:dg005` / `daido:auth_url` / `daido:auth_code` を書いて push。
- 接続: `auth_url` → logs/auth_url.txt の URL（空白を詰める）を開き、大道芸専門アカデミーのチャンネルでログイン → リダイレクト先 URL を `daido/jobs/auth_code.txt` に書いて `daido:auth_code`。以後 channel_id.txt のチャンネルにだけ投稿する。
