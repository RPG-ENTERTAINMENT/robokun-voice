# sugo — スゴ技スクールRPG 宣伝ショート自動投稿

毎日2本（7:00 / 18:00 JST 予約公開）。キャラが動く15秒前後の縦動画＋VOICEVOX（春日部つむぎ / ずんだもん）ナレーション。
`scripts/daily.sh` の 01:40 JST（失敗時の再試行 12:30 JST）の実行後に `bash sugo/run.sh daily` が走る。

- `episodes.py` … ネタ帳（コース紹介8＋FAQ8＋ストーリー1）。ネタを足すときはここに追加し SAY に台本を足す。順番に回る（state/state.json の next）。
- `main.py` … daily / smoke / render <id>。`channel_id.txt` のチャンネル以外には投稿しない。
- `chara.py` `engine.py` … 描画エンジン（code_b64 に格納、初回実行時に展開）。素材は assets_b64。
- 接続: jobs/daily_task に `sugo:auth_url` → logs/auth_url.txt を開く → ログイン → jobs/auth_code.txt に URL → `sugo:auth_code`。
- 音声クレジット「VOICEVOX:春日部つむぎ」は動画内と説明欄に必須。
