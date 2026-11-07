# ninja — CRAZY NINJA SHIZUKU しずく社長（YouTube @crazyninjajapan）忍者しずくチャレンジショート

毎日1本（12:00 JST 予約公開）。NINJA DIGITAL BAR で忍者しずくが手裏剣・フルーツ斬り・キャッチ・忍術・カラオケ・動く的に挑戦する英語ショート。
BGM・効果音はその場で合成（外部音源なし）、最後に rpgtokyo.com/ninjabar のQRコード。1コマ目がそのままサムネになる作り。

- 台本: `engine/gen.py` が話数 n から自動生成（6種類を順番に、n で毎回ちがう）。state/state.json の next で順に回る。
- 描画: `engine/render.py`（背景 bg.py・音 audio.py）。ポーズ画像は assets/sprites.webp.b64.*（実行時に1枚に戻す）、位置は sprites.json。フォントは実行時に google/fonts から取得。
- 実行: `scripts/daily.sh` の 01:40 JST の実行後（失敗時の再試行 12:30 JST）に `bash ninja/run.sh daily`。手動は `jobs/daily_task` に `ninja:test` / `ninja:test:7` / `ninja:auth_url` / `ninja:auth_code` を書いて push。
- 接続: `auth_url` → logs/auth_url.txt の URL（空白を詰める）を開き、CRAZY NINJA SHIZUKU のチャンネルでログイン → リダイレクト先 URL を `ninja/jobs/auth_code.txt` に書いて `ninja:auth_code`。以後 channel_id.txt のチャンネルにだけ投稿する（無ければ投稿しない）。
