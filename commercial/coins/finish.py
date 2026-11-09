"""Subtitles, title cards, the end card and the sound mix for "Wait... they're COINS?".
python3 finish.py FRAMES_DIR OUT_DIR   (FRAMES_DIR: f_0001..f_0880.png from the render) -> OUT_DIR/c_####.png + mix.wav"""
import os, sys, json, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, '..', 'assets'); AU = os.path.join(HERE, 'audio')
FR, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
W, H = 720, 1280; FPS = 30; N3D = 880; END = 964
VO = json.load(open(os.path.join(AU, 'vo', 'lines.json')))
LINES = [('k_useless', 0.8), ('k_dollar', 5.0), ('k_real', 11.2), ('k_list', 13.4), ('k_chill', 16.95), ('k_research', 18.6),
         ('k_three', 23.0), ('k_mom', 24.9), ('m_bed', 27.5)]
def font(s): return ImageFont.truetype(os.path.join(A, 'lilita.ttf'), s)
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def pop(t, t0, d=0.25):
    u = (t - t0) / d
    if u <= 0: return 0.0
    return 1.0 if u >= 1 else (1 + 0.2 * math.sin(u * math.pi)) * ease(u)
def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        nx = (cur + ' ' + w).strip()
        if d.textlength(nx, font=f) > maxw and cur: lines.append(cur); cur = w
        else: cur = nx
    return lines + [cur]
def stamp(base, text, size, cx, cy, k, fill=(255, 255, 255), stroke=7):
    if k <= 0.01: return
    f = font(size); bb = f.getbbox(text, stroke_width=stroke)
    im = Image.new('RGBA', (bb[2] - bb[0] + 10, bb[3] - bb[1] + 10), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((5 - bb[0], 5 - bb[1]), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(20, 10, 48))
    w, h = int(im.width * k), int(im.height * k)
    if w > 2 and h > 2: base.alpha_composite(im.resize((w, h), Image.LANCZOS), (int(cx - w / 2), int(cy - h / 2)))

LOGO = Image.open(os.path.join(A, 'logo.png')).convert('RGBA')
def frame(f):
    t = (f - 1) / FPS
    if f <= N3D: base = Image.open(os.path.join(FR, f'f_{f:04d}.png')).convert('RGBA')
    else: base = Image.open(os.path.join(FR, f'f_{N3D:04d}.png')).convert('RGBA').filter(ImageFilter.GaussianBlur(12))
    d = ImageDraw.Draw(base)
    if f <= N3D:
        # subtitles
        for i, t0 in LINES:
            if t0 <= t < t0 + VO[i]['dur'] + 0.25:
                who = '' if VO[i]['who'] == 'kyle' else 'MOM (off): '
                f_ = font(40); lines = wrap(d, who + VO[i]['text'], f_, W - 90)
                for j, ln in enumerate(lines):
                    d.text((W / 2, H - 230 + j * 50 - (len(lines) - 1) * 50), ln, font=f_, fill=(255, 255, 255) if not who else (255, 214, 120),
                           stroke_width=5, stroke_fill=(10, 10, 16), anchor='mm')
        # the opening card and the comic beats
        if t < 3.4:
            a = 1 - ease((t - 2.9) / 0.5)
            stamp(base, '3:12 AM', 70, W / 2, 150, pop(t, 0.2) * a)
            stamp(base, 'one more game.', 40, W / 2, 215, pop(t, 0.5) * a, (255, 214, 80), 5)
        if 11.2 <= t < 13.2: stamp(base, 'WAIT.', 110, W / 2, 230, pop(t, 11.25), (255, 80, 90))
        for k, (tk, txt) in enumerate([(13.25, '$LMAO'), (14.15, '$KET'), (15.05, '$PEPE'), (15.95, '$CHILLGUY')]):
            if tk <= t < tk + 0.85: stamp(base, txt, 92, W / 2 + (-90 if k % 2 else 90), 190 + 40 * (k % 2), pop(t, tk, 0.18), (90, 240, 120))
        if 20.2 <= t < 21.6: stamp(base, '*research*', 76, W / 2, 210, pop(t, 20.25), (255, 214, 80))
        if 22.6 <= t < 24.6: stamp(base, 'BALANCE: $3.12', 64, W / 2, 200, pop(t, 22.65), (255, 90, 100))
        if 27.4 <= t: stamp(base, '3 AM.', 90, W / 2, 200, pop(t, 27.5))
    else:   # end card
        base.alpha_composite(Image.new('RGBA', (W, H), (20, 10, 48, 175)))
        u = t - N3D / FPS
        stamp(base, 'EVERY CARD', 84, W / 2, 230, pop(u, 0.05)); stamp(base, 'IS A REAL', 84, W / 2, 320, pop(u, 0.2))
        stamp(base, 'MEME COIN.', 96, W / 2, 420, pop(u, 0.35), (90, 240, 120))
        lg = LOGO.copy(); lg.thumbnail((430, 430)); k = pop(u, 0.6)
        if k > 0.01:
            w, h = int(lg.width * k), int(lg.height * k); base.alpha_composite(lg.resize((w, h)), (int(W / 2 - w / 2), int(700 - h / 2)))
        stamp(base, 'PLAY FREE', 80, W / 2, 970, pop(u, 0.9))
        if u > 1.1:
            d.rounded_rectangle((70, 1040, W - 70, 1108), 30, fill=(255, 214, 80)); d.text((W / 2, 1074), 'memeroyale.imaginestudio.fun', font=font(36), fill=(20, 10, 48), anchor='mm')
        d.text((W / 2, 1200), 'not financial advice. definitely gaming advice.', font=font(26), fill=(200, 200, 215), anchor='mm')
    base.convert('RGB').save(os.path.join(OUT, f'c_{f:04d}.png'))

if not os.environ.get('MIXONLY'):
    for f in range(1, END + 1): frame(f)
    print('FRAMES-DONE')
# ---------------------------------------------------------------- sound
cues = [(f'vo/{i}.wav', t0, 1.0) for i, t0 in LINES]
cues += [('ui_tap.mp3', 4.55, 0.7), ('emote_pop.mp3', 4.95, 0.8), ('ui_tap.mp3', 9.0, 0.6), ('ui_swoosh.mp3', 9.7, 0.6),
         ('coins.mp3', 11.25, 0.8), ('emote_pop.mp3', 13.25, 0.9), ('emote_pop.mp3', 14.15, 0.9), ('emote_pop.mp3', 15.05, 0.9),
         ('coin_jingle.mp3', 15.95, 0.9), ('w_fanfare.mp3', 20.2, 0.6), ('ui_tap.mp3', 22.05, 0.8), ('card_deny.mp3', 22.6, 1.0),
         ('victory.mp3', N3D / FPS + 0.1, 0.8)]
ins = ['-i', os.path.join(AU, 'mus_battle_lofi.mp3')]
flt = [f"[0:a]atrim=0:{END / FPS},volume=0.16,afade=t=in:d=0.8,afade=t=out:st={END / FPS - 1.2}:d=1.2[m]"]
for j, (p, t0, v) in enumerate(cues):
    ins += ['-i', os.path.join(AU, p)]; ms = int(t0 * 1000)
    flt.append(f'[{j + 1}:a]aresample=48000,adelay={ms}|{ms},volume={v}[a{j}]')
flt.append('[m]' + ''.join(f'[a{j}]' for j in range(len(cues))) + f'amix=inputs={len(cues) + 1}:normalize=0:duration=first,alimiter=limit=0.9[out]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[out]', '-ac', '2', '-ar', '48000', os.path.join(OUT, 'mix.wav')], check=True)
print('MIX-DONE')
