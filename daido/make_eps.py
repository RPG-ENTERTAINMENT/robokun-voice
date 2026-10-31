import json, os
S = '大道芸専門アカデミー'
END = lambda t='だいどうげい、オンラインで ならえるよ。': {"robo": {"pose": "joy"}, "hana": {"eyes": "happy"}, "fx": ["confetti"], "music": "happy", "say": {"who": "narr", "text": t}, "cam": "wide", "focus": "both", "dur": 2.6}
def R(text, pose=None, **k):
    b = {"say": {"who": "robo", "text": text}}
    if pose: b["robo"] = {"pose": pose}
    b.update(k); return b
def H(text, eyes=None, **k):
    b = {"say": {"who": "hana", "text": text}}
    if eyes: b["hana"] = {"eyes": eyes}
    b.update(k); return b
def N(text, **k):
    b = {"say": {"who": "narr", "text": text}}; b.update(k); return b
EPS = [
 ("dg001", "はじめての ジャグリング", "ロボしず、ジャグリングに挑戦！", "day", [
  N("ロボしず、だいどうげいに ちょうせん！", fx=["sparkles"], cam="wide", focus="both"),
  R("ボールを みっつ なげるんだって。", "think", cam="mid"),
  H("いきなり みっつ？", "open"),
  R("えいっ！", "joy", fx=["juggle_fail"], sfx=["whoosh_small"], cam="close", focus="robo"),
  R("…ぜんぶ おちた。", "damage", sfx=["bonk"], fx=["puff"]),
  H("さいしょは ひとつから だよ。", "happy", cam="mid", focus="both"),
  R("ひとつ… ふたつ… みっつ…", "closed", music="magic"),
  R("できた！", "joy", fx=["juggle"], sfx=["tada"], cam="close", focus="robo", dur=3.2),
  H("すごい！ ちゃんと まわってる！", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END()]),
 ("dg002", "なげせんの ひみつ", "投げ銭がたくさん入る大道芸人の共通点", "day", [
  N("きょうは はじめての ろじょう ショー。", cam="wide", focus="both"),
  R("みてみて！ ジャグリング！", "joy", fx=["juggle"], sfx=["whoosh_small"], dur=3.0, cam="mid"),
  H("じょうず！ でも… おかね はいらないね。", "sad"),
  R("どうして？", "trouble", fx=["sweat"]),
  H("さいごに おねがい してないもん。", "open"),
  R("おねがい？", "surprise", fx=["ding"]),
  R("たのしかったら、ぼうしに おきもちを！", "smile", cam="close", focus="robo"),
  N("チャリン、チャリン。", fx=["coins"], sfx=["ding"], music="playful", dur=3.0, cam="wide"),
  R("はいった！", "joy", fx=["sparkles"]),
  END("さいごの ひとことも、ならえるよ。")]),
 ("dg003", "バルーンアート", "犬を作るはずが…ロボしずのバルーンアート", "morning", [
  N("きょうは バルーンアートの れんしゅう。", cam="wide", focus="both"),
  H("いぬ つくって！", "happy"),
  R("まかせて！ ふーっ！", "joy", fx=["balloon"], sfx=["swoosh_up"], cam="close", focus="robo", dur=2.4),
  R("…できた！", "joy"),
  H("それ、ハートだよ。", "open", cam="mid", focus="both"),
  R("…ほんとだ。", "shy", fx=["sweat"]),
  H("でも、いちばん うれしい かたち。", "happy", fx=["glow_hana"]),
  R("じゃあ、ハナに プレゼント。", "love", fx=["hearts"], music="lullaby"),
  END("バルーンも、いちから おしえるよ。")]),
 ("dg004", "パントマイムの かべ", "パントマイムの壁、一番大事なのは？", "day", [
  N("ロボしず、パントマイムに ちょうせん。", cam="wide", focus="both"),
  R("ここに かべが ある… ある…", "think", cam="mid"),
  H("てだけ うごいてるよ。", "open"),
  R("え？", "surprise", fx=["ding"]),
  H("からだぜんぶで、ピタッと とまるの。", "happy"),
  R("ピタッ。", "closed", sfx=["pop"], cam="close", focus="robo", dur=1.8),
  H("あ！ かべが みえた！", "happy", fx=["glow_hana"], music="magic"),
  R("とまる ことが、いちばん むずかしいんだね。", "smile", cam="mid", focus="both"),
  END("みえない かべも、みえるように なるよ。")]),
 ("dg005", "おきゃくさんが こない", "人が集まらない大道芸、何が足りない？", "sunset", [
  N("ろじょうで まって、いちじかん。", music="sad", cam="wide", focus="both"),
  R("だれも こない…", "sad"),
  H("まってるだけじゃ、とまって くれないよ。", "open"),
  R("どうすれば いい？", "trouble", fx=["sweat"]),
  H("さきに、おおきな こえで よぶの！", "happy"),
  R("さあさあ、よって らっしゃい！", "joy", fx=["spot"], sfx=["tada"], music="playful", cam="close", focus="robo"),
  N("あっという まに、ひとだかり。", fx=["coins"], sfx=["ding"], dur=3.0, cam="wide"),
  R("ひとを あつめるのも、げいの ひとつ！", "joy", fx=["sparkles"]),
  END("ひとの あつめかたも、ならえるよ。")]),
 ("dg006", "とおくても ならえる？", "大道芸、近くに教室がなくても習える？", "morning", [
  H("だいどうげい、ならいたいけど…", "sad", cam="mid", focus="both"),
  H("ちかくに きょうしつが ないの。", "sad"),
  R("だいじょうぶ！", "joy", fx=["ding"]),
  R("ビデオ つうわで、おうちから ならえるよ。", "smile", cam="close", focus="robo"),
  H("ほんと？", "open"),
  R("まいしゅう、プロが ショーを みてくれる。", "joy", fx=["sparkles"], music="magic"),
  H("じゃあ、わたしも できるかも！", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END("ぜんこく どこからでも、かよえるよ。")]),
 ("dg007", "いそがしくても", "仕事が忙しくても大道芸は習える？", "night", [
  H("しごとが いそがしくて…", "sad", music="night", cam="mid", focus="both"),
  H("ならいごとの じかんが ないの。", "sad"),
  R("じかんは、せんせいと あわせられるよ。", "smile", fx=["ding"]),
  H("すきな じかんで いいの？", "open"),
  R("うん！ まいしゅう、すきな じかんに。", "joy", fx=["sparkles"], music="magic"),
  R("よるの れんしゅうも、たのしいよ。", "joy", fx=["juggle"], sfx=["whoosh_small"], dur=3.0, cam="close", focus="robo"),
  H("それなら つづけられそう！", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END("すきな じかんに、オンラインで まなべるよ。")]),
 ("dg008", "5ふんの ショー", "大道芸のショーは5分あれば作れる", "day", [
  R("ショーって、どう つくるの？", "think", cam="mid", focus="both"),
  H("ながれは よっつ だよ。", "open"),
  N("ひとつめ、つかみ。", fx=["ding"], sfx=["pop"]),
  N("ふたつめ、みせば。", fx=["juggle"], sfx=["whoosh_small"], dur=2.6),
  N("みっつめ、もりあげ。", fx=["spot"], music="playful"),
  N("よっつめ、しめ。", fx=["coins"], sfx=["ding"], dur=2.6),
  R("これで ごふんの ショーが できる！", "joy", fx=["sparkles"], cam="close", focus="robo"),
  H("ロボしず、もう プロみたい！", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END("ショーの つくりかたも、ならえるよ。")]),
 ("dg009", "ひとまえが こわい", "人前に立つのが苦手でもパフォーマーになれる？", "day", [
  R("ひとまえに たつと、ドキドキする…", "shy", fx=["sweat"], cam="mid", focus="both"),
  H("みんな、さいしょは そうだよ。", "open"),
  R("ほんとに？", "surprise"),
  H("たちかたと、めせんと、ま。", "happy"),
  H("れんしゅうすれば、ぜったい みにつくよ。", "happy", fx=["glow_hana"]),
  R("よし…！", "closed", music="magic", cam="close", focus="robo"),
  R("みなさん、こんにちは！", "joy", fx=["spot"], sfx=["tada"], dur=2.4),
  N("はくしゅ かっさい。", fx=["confetti"], sfx=["tada"], cam="wide"),
  END("じしんの つけかたも、ならえるよ。")]),
 ("dg010", "しごとに なる？", "大道芸って仕事になるの？", "sunset", [
  H("だいどうげいって、しごとに なるの？", "open", cam="mid", focus="both"),
  R("イベントや テーマパーク、テレビ。", "think"),
  R("ショーを さがしてる ひとは、たくさん いるよ。", "smile", fx=["ding"]),
  H("でも、どうやって しごとを もらうの？", "sad"),
  R("えいぎょうの しかたも、ならえるんだ。", "joy", fx=["sparkles"], music="magic", cam="close", focus="robo"),
  H("すきなことが しごとに なるんだね！", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END("しゅうしょく コースも あるよ。")]),
 ("dg011", "ひとつの ボール", "ジャグリング上達のコツは「1個」", "morning", [
  R("きょうも、みっつで れんしゅう！", "joy", cam="mid", focus="both"),
  H("ちょっと まって。", "open"),
  H("ひとつを きれいに なげられる？", "open"),
  R("ひとつなんて かんたん… あれ？", "surprise", fx=["sweat"]),
  R("たかさが ばらばら だ…", "trouble"),
  H("ひとつが きれいなら、みっつも きれい。", "happy", music="magic"),
  R("おなじ たかさ、おなじ リズム…", "closed", cam="close", focus="robo"),
  R("できた！ きれいに まわる！", "joy", fx=["juggle"], sfx=["tada"], dur=3.0),
  END("きほんから、じゅんばんに おしえるよ。")]),
 ("dg012", "ゆめの ぶたい", "大道芸人の夢の舞台、知ってる？", "night", [
  H("ロボしずの ゆめは なに？", "open", music="night", cam="mid", focus="both"),
  R("せかいの ぶたいで、ショーを すること。", "think"),
  H("せかい！？", "happy", fx=["ding"]),
  R("かいがいの おまつりにも、よばれる ひとが いるんだよ。", "smile"),
  R("いつか ぼくも…", "closed", music="magic", cam="close", focus="robo"),
  R("せかいじゅうで、ジャグリング！", "joy", fx=["juggle"], sfx=["whoosh_small"], dur=3.0),
  H("わたし、さいしょの おきゃくさんに なる。", "happy", fx=["glow_hana"], cam="mid", focus="both"),
  END("かいがいを めざす みちも、あるよ。")]),
 ("dg013", "ひとりで れんしゅう", "独学の大道芸、伸び悩む理由", "rainy", [
  R("どうがを みて、ひとりで れんしゅう。", "think", music="rainy", cam="mid", focus="both"),
  R("でも、なにが ダメか わからない…", "sad"),
  H("じぶんでは、きづきにくいよね。", "open"),
  R("どうしよう…", "trouble", fx=["sweat"]),
  H("プロに みてもらえば、すぐ わかるよ。", "happy", fx=["ding"]),
  R("まいしゅう みてもらえたら…", "think", music="magic"),
  R("もっと はやく うまくなる！", "joy", fx=["juggle"], sfx=["tada"], dur=3.0, cam="close", focus="robo"),
  END("まいしゅう、プロが ショーを みるよ。")]),
 ("dg014", "がっこうが はじまる", "大道芸専門アカデミー、開校！", "morning", [
  N("ロボしずから、おしらせです。", fx=["sparkles"], cam="wide", focus="both"),
  R("だいどうげいの がっこうが、できました！", "joy", fx=["spot"], sfx=["tada"], cam="close", focus="robo"),
  H("どんな がっこう？", "open", cam="mid", focus="both"),
  R("プロの せんせいが、まいしゅう ショーを みてくれる。", "smile"),
  R("オンラインで、すきな じかんに。", "joy", fx=["ding"]),
  H("はじめてでも だいじょうぶ？", "open"),
  R("ゼロから はじめる ひとが、ほとんど だよ。", "smile", fx=["juggle"], sfx=["whoosh_small"], dur=3.0),
  H("わくわく するね！", "happy", fx=["glow_hana"], music="magic"),
  END("むりょう そうだんは、LINEから。")]),
]
TIMEMAP = {"rainy": ("day", "rain")}
os.makedirs('episodes', exist_ok=True); idx = []
for eid, title, yt, tm, beats in EPS:
    time, weather = TIMEMAP.get(tm, (tm, 'clear'))
    ep = {"id": eid, "title": title, "series": S, "yt_title": yt, "time": time, "weather": weather,
          "music": "playful", "robo_x": 820, "robo_pose": "idle", "hana": {"x": 1240, "bloom": 1, "droop": 0}, "beats": beats}
    json.dump(ep, open(f'episodes/{eid}.json', 'w'), ensure_ascii=False, indent=1); idx.append(eid)
json.dump(idx, open('index.json', 'w'))
print(len(idx), 'episodes')
