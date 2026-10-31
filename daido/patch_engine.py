"""大道芸専門アカデミー用の追加演出を eng/engine_l.py に足す（shorts_tempo.py の後に実行）。
fx: juggle（3つのボールでジャグリング） / juggle_fail（ボールが落ちる） / balloon（バルーンがふくらむ）
    coins（投げ銭がハットに入る） / spot（スポットライト）
画面下部に「大道芸専門アカデミー 生徒募集中」の帯を常に表示する。"""
import sys
f = sys.argv[1] if len(sys.argv) > 1 else 'eng/engine_l.py'
src = open(f, encoding='utf-8').read()

PROPS_LINE = "PROPS = {k: _prop(k) for k in ['apple', 'star', 'acorn', 'umbrella', 'leaf', 'note', 'bulb', 'sweat']}\n"
ADD_PROPS = PROPS_LINE + r'''
# ---------- 大道芸 props
def _dg_ball(col):
    S = 3; im = Image.new('RGBA', (60*S, 60*S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([2*S, 2*S, 58*S, 58*S], fill=(74, 58, 46, 255)); d.ellipse([6*S, 6*S, 54*S, 54*S], fill=col+(255,))
    d.ellipse([16*S, 13*S, 28*S, 25*S], fill=(255, 255, 255, 170))
    im = im.resize((60, 60), Image.LANCZOS); a = np.asarray(im).astype(np.float32)/255.; a[..., :3] *= a[..., 3:4]; return a
DG_BALLS = [_dg_ball(c) for c in ((235, 80, 80), (80, 150, 240), (250, 205, 60))]
def _dg_balloon():
    S = 3; im = Image.new('RGBA', (160*S, 260*S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); O = (74, 58, 46, 255)
    for (x0, y0, x1, y1) in ((30, 20, 90, 90), (70, 20, 130, 90), (40, 75, 120, 150)):
        d.ellipse([x0*S, y0*S, x1*S, y1*S], fill=O); d.ellipse([(x0+4)*S, (y0+4)*S, (x1-4)*S, (y1-4)*S], fill=(240, 110, 160, 255))
    for (x0, y0) in ((44, 34), (84, 34), (56, 90)): d.ellipse([x0*S, y0*S, (x0+14)*S, (y0+14)*S], fill=(255, 220, 235, 200))
    d.line([(80*S, 150*S), (80*S, 255*S)], fill=O, width=3*S)
    im = im.resize((160, 260), Image.LANCZOS); a = np.asarray(im).astype(np.float32)/255.; a[..., :3] *= a[..., 3:4]; return a
DG_BALLOON = _dg_balloon()
def _dg_hat():
    S = 3; im = Image.new('RGBA', (200*S, 120*S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); O = (40, 32, 30, 255)
    d.ellipse([4*S, 70*S, 196*S, 116*S], fill=O); d.ellipse([10*S, 74*S, 190*S, 110*S], fill=(55, 50, 70, 255))
    d.rectangle([50*S, 10*S, 150*S, 92*S], fill=O); d.rectangle([56*S, 16*S, 144*S, 90*S], fill=(60, 55, 80, 255))
    d.rectangle([56*S, 62*S, 144*S, 76*S], fill=(220, 70, 80, 255))
    im = im.resize((200, 120), Image.LANCZOS); a = np.asarray(im).astype(np.float32)/255.; a[..., :3] *= a[..., 3:4]; return a
DG_HAT = _dg_hat()
def _dg_coin():
    S = 3; im = Image.new('RGBA', (40*S, 40*S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([2*S, 2*S, 38*S, 38*S], fill=(150, 110, 30, 255)); d.ellipse([5*S, 5*S, 35*S, 35*S], fill=(250, 210, 80, 255))
    im = im.resize((40, 40), Image.LANCZOS); a = np.asarray(im).astype(np.float32)/255.; a[..., :3] *= a[..., 3:4]; return a
DG_COIN = _dg_coin()
_DG_BANNER = {}
def dg_banner(C):
    if 'im' not in _DG_BANNER:
        f1 = font(FONT_T, 44); txt = '大道芸専門アカデミー  生徒募集中'
        w = f1.getbbox(txt)[2]; bw, bh = w+70, 84
        im = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, bw-1, bh-1], radius=42, fill=(28, 30, 60, 225), outline=(235, 192, 106, 255), width=4)
        d.text((35, 14), txt, font=f1, fill=(255, 236, 190))
        _DG_BANNER['im'] = (to_prem(im), bw, bh)
    im, bw, bh = _DG_BANNER['im']
    blit(C, im, Mx(CX, (60 if LAND else 1580), 1, bw/2, bh/2))
'''
assert PROPS_LINE in src, 'props anchor'
src = src.replace(PROPS_LINE, ADD_PROPS, 1)

FG = "        blit(C, LAY['fg'], layer_M(2300, cx, cy, z, 1220/1020))\n"
ADD_FX = r'''        # ---------- 大道芸 fx
        for (t0, f, d) in s.fx:
            v = t-t0
            if v < 0: continue
            hx, hy = robo_head
            if f == 'juggle' and v < 3.4:
                op = ss(v/0.2)*(1-ss((v-3.1)/0.3))
                for i in range(3):
                    ph = (v*1.25+i/3.0) % 1.0
                    X = hx+150*zz*math.cos(2*math.pi*ph); Y = hy-40*zz-210*zz*abs(math.sin(math.pi*ph))+60*zz*math.sin(2*math.pi*ph)
                    blit(C, DG_BALLS[i], Mx(X, Y, zz*1.25, 30, 30), op)
            elif f == 'juggle_fail' and v < 1.8:
                for i in range(3):
                    sx = (-1, 0.3, 1)[i]; vy = (-900, -1100, -800)[i]
                    X = hx+sx*260*zz*v; Y = hy-40*zz+vy*zz*v+1500*zz*v*v
                    gy = gs(0, GROUND_Y-15)[1]
                    if Y > gy: Y = gy
                    blit(C, DG_BALLS[i], Mx(X, Y, zz*1.25, 30, 30), 1-ss((v-1.4)/0.4))
            elif f == 'balloon' and v < 3.4:
                g = ease_out_back(min(v/0.7, 1), 1.4); op = 1-ss((v-3.0)/0.4)
                blit(C, DG_BALLOON, Mx(hx+170*zz, hy+40*zz-v*20*zz, zz*(0.4+0.75*g), 80, 250, math.sin(v*3)*0.08), op)
            elif f == 'coins' and v < 3.4:
                hp = gs(d['x']+200, GROUND_Y+20); op = 1-ss((v-3.0)/0.4)
                blit(C, DG_HAT, Mx(*hp, zz*0.9, 100, 110), op)
                for i in range(5):
                    vv = v-0.25-i*0.35
                    if 0 < vv < 0.7:
                        u = vv/0.7; X = hp[0]+(1-u)*420*zz; Y = hp[1]-60*zz-520*zz*math.sin(math.pi*min(u*0.9+0.1, 1))*(1-u)-30*zz*u
                        blit(C, DG_COIN, Mx(X, Y, zz*1.1, 20, 20, vv*9), op)
            elif f == 'spot' and v < 3.4:
                g = ss(v/0.4)*(1-ss((v-2.8)/0.6))
                blit(C, GLOW, Mx(hx, hy+260*zz, zz*2.4, 220, 220), g*0.55)
'''
assert FG in src, 'fg anchor'
src = src.replace(FG, ADD_FX+FG, 1)

OUT = "        out = O[..., :3]\n        fo = ss("
assert OUT in src, 'banner anchor'
src = src.replace(OUT, "        dg_banner(O)\n"+OUT, 1)
open(f, 'w', encoding='utf-8').write(src)
print('daido patch applied')
