import random, math, json, os
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(OUT, exist_ok=True)
W, H = 1600, 1200  # drawn at 2x, saved at 800x600

def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)

def background(seed):
    r = random.Random(seed)
    base = r.choice([(214, 200, 178), (190, 196, 204), (226, 222, 214), (168, 150, 128), (205, 210, 200)])
    img = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(img)
    # wood grain / table texture
    for y in range(0, H, 6):
        f = 1 + 0.05 * math.sin(y / 37.0 + r.random()) + r.uniform(-0.02, 0.02)
        d.line([(0, y), (W, y + r.randint(-8, 8))], fill=shade(base, f), width=6)
    # vignette
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * .2, -H * .2, W * 1.2, H * 1.2], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGB", (W, H), shade(base, .72))
    return Image.composite(img, dark, vig)

def shadow(img, shape_fn):
    m = Image.new("L", (W, H), 0)
    shape_fn(ImageDraw.Draw(m))
    m = m.filter(ImageFilter.GaussianBlur(30))
    s = Image.new("RGB", (W, H), (40, 35, 30))
    off = Image.new("L", (W, H), 0); off.paste(m, (24, 30))
    off = off.point(lambda v: int(v * .45))
    img.paste(s, (0, 0), off)

def rr(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

# ---------- items ----------
def bottle(img, c, extra):
    d = ImageDraw.Draw(img)
    shadow(img, lambda m: m.rounded_rectangle([640, 230, 960, 1060], 110, fill=255))
    d = ImageDraw.Draw(img)
    rr(d, [640, 300, 960, 1060], 110, c)
    d.rectangle([660, 330, 700, 1020], fill=shade(c, 1.18))  # highlight
    rr(d, [690, 170, 910, 320], 40, extra.get("cap", (40, 40, 45)))
    rr(d, [740, 120, 860, 190], 30, extra.get("cap", (40, 40, 45)))
    if extra.get("sticker"):
        sc = extra["sticker"]
        d.ellipse([730, 560, 880, 710], fill=(250, 250, 250))
        d.ellipse([748, 578, 862, 692], fill=sc)
        d.polygon([(805, 595), (840, 665), (770, 665)], fill=(250, 250, 250))
    if extra.get("band"):
        d.rectangle([640, 820, 960, 860], fill=extra["band"])

def hoodie(img, c, extra):
    def body(m, fill=255):
        m.polygon([(480, 330), (1120, 330), (1360, 820), (1240, 880), (1080, 560), (1080, 1080), (520, 1080), (520, 560), (360, 880), (240, 820)], fill=fill)
    shadow(img, body)
    d = ImageDraw.Draw(img)
    body(d, c)
    d.ellipse([640, 210, 960, 470], fill=shade(c, .8))
    d.ellipse([700, 260, 900, 440], fill=shade(c, .55))
    rr(d, [620, 800, 980, 1000], 30, shade(c, .88))
    d.line([(760, 440), (740, 640)], fill=extra.get("string", (235, 235, 235)), width=10)
    d.line([(840, 440), (860, 640)], fill=extra.get("string", (235, 235, 235)), width=10)
    if extra.get("logo"):
        d.text((735, 650), extra["logo"], fill=extra.get("logo_c", (240, 240, 240)), font_size=72)
    for x in (520, 1080):
        d.line([(x, 560), (x, 1080)], fill=shade(c, .82), width=6)

def puffer(img, c, extra):
    def body(m, fill=255):
        m.polygon([(500, 300), (1100, 300), (1340, 860), (1220, 900), (1080, 580), (1080, 1090), (520, 1090), (520, 580), (380, 900), (260, 860)], fill=fill)
    shadow(img, body)
    d = ImageDraw.Draw(img)
    body(d, c)
    for y in range(360, 1090, 90):
        d.line([(520, y), (1080, y)], fill=shade(c, .75), width=8)
    d.line([(800, 300), (800, 1090)], fill=(200, 200, 205), width=10)
    rr(d, [640, 240, 960, 330], 30, shade(c, .85))

def backpack(img, c, extra):
    shadow(img, lambda m: m.rounded_rectangle([500, 220, 1100, 1080], 140, fill=255))
    d = ImageDraw.Draw(img)
    d.arc([660, 110, 940, 330], 180, 360, fill=shade(c, .6), width=34)
    rr(d, [500, 220, 1100, 1080], 140, c)
    rr(d, [580, 640, 1020, 1030], 70, shade(c, .85))
    d.line([(620, 690), (980, 690)], fill=(60, 60, 60), width=8)
    d.line([(560, 330), (1040, 330)], fill=(60, 60, 60), width=8)
    d.rectangle([965, 680, 985, 740], fill=(200, 200, 200))
    if extra.get("patch"):
        d.ellipse([720, 760, 880, 920], fill=extra["patch"])
    if extra.get("keychain"):
        d.line([(1080, 380), (1150, 520)], fill=(190, 190, 190), width=8)
        d.ellipse([1110, 500, 1210, 600], fill=extra["keychain"])

def lunchbox(img, c, extra):
    shadow(img, lambda m: m.rounded_rectangle([440, 380, 1160, 1000], 60, fill=255))
    d = ImageDraw.Draw(img)
    d.arc([660, 240, 940, 470], 180, 360, fill=(40, 40, 40), width=30)
    rr(d, [440, 380, 1160, 1000], 60, c)
    rr(d, [440, 380, 1160, 520], 60, shade(c, .85))
    d.line([(470, 520), (1130, 520)], fill=(70, 70, 70), width=8)
    if extra.get("print"):
        r = random.Random(1)
        for _ in range(14):
            x, y = r.randint(500, 1080), r.randint(560, 940)
            d.ellipse([x, y, x + 46, y + 46], fill=extra["print"])

def calculator(img, c, extra):
    shadow(img, lambda m: m.rounded_rectangle([560, 140, 1040, 1100], 50, fill=255))
    d = ImageDraw.Draw(img)
    rr(d, [560, 140, 1040, 1100], 50, c)
    rr(d, [620, 210, 980, 420], 16, (150, 168, 150))
    d.text((650, 340), "12.5x+3", fill=(30, 40, 30), font_size=54)
    keyc = extra.get("keys", (60, 60, 66))
    for row in range(7):
        for col in range(5):
            x = 620 + col * 74; y = 480 + row * 82
            rr(d, [x, y, x + 56, y + 50], 10, keyc if row > 1 else extra.get("top", (90, 140, 200)))
    if extra.get("initials"):
        d.text((620, 1040), extra["initials"], fill=(245, 245, 245), font_size=44)

def notebook(img, c, extra):
    shadow(img, lambda m: m.rectangle([520, 180, 1080, 1060], fill=255))
    d = ImageDraw.Draw(img)
    d.rectangle([520, 180, 1080, 1060], fill=c)
    for y in range(220, 1040, 56):
        d.ellipse([500, y, 548, y + 30], outline=(160, 160, 165), width=8)
    rr(d, [640, 330, 980, 470], 10, (245, 245, 240))
    if extra.get("label"):
        d.text((670, 365), extra["label"], fill=(40, 40, 120), font_size=60)
    if extra.get("marble"):
        r = random.Random(3)
        for _ in range(400):
            x, y = r.randint(520, 1070), r.randint(180, 1050)
            d.ellipse([x, y, x + 8, y + 8], fill=(240, 240, 240))
        rr(d, [640, 330, 980, 470], 10, (245, 245, 240))
        d.text((670, 365), "COMP", fill=(30, 30, 30), font_size=60)

def glasses(img, c, extra):
    shadow(img, lambda m: (m.ellipse([400, 480, 760, 760], fill=255), m.ellipse([840, 480, 1200, 760], fill=255)))
    d = ImageDraw.Draw(img)
    for x in (400, 840):
        d.rounded_rectangle([x, 480, x + 360, 760], 120, outline=c, width=34, fill=(205, 215, 222))
    d.arc([740, 520, 860, 640], 200, 340, fill=c, width=26)
    d.line([(410, 560), (220, 520)], fill=c, width=24)
    d.line([(1190, 560), (1380, 520)], fill=c, width=24)
    if extra.get("case"):
        rr(d, [500, 860, 1100, 1060], 100, extra["case"])

def keys(img, c, extra):
    d = ImageDraw.Draw(img)
    d.ellipse([620, 380, 860, 620], outline=(175, 175, 180), width=22)
    for i, ang in enumerate((-20, 25)):
        cx, cy = 780 + i * 60, 600
        poly = [(cx, cy), (cx + 60, cy), (cx + 60, cy + 360), (cx + 30, cy + 420), (cx, cy + 360)]
        poly = [(x + i * 50, y) for x, y in poly]
        d.polygon(poly, fill=(200, 175, 90) if i == 0 else (190, 190, 195))
        d.ellipse([cx - 40 + i * 50, cy - 80, cx + 100 + i * 50, cy + 40], fill=(200, 175, 90) if i == 0 else (190, 190, 195))
    d.line([(650, 420), (330, 160)], fill=c, width=40)
    d.line([(700, 390), (420, 120)], fill=c, width=40)
    if extra.get("charm"):
        d.ellipse([520, 640, 660, 780], fill=extra["charm"])

def headphones(img, c, extra):
    d = ImageDraw.Draw(img)
    d.arc([460, 200, 1140, 900], 180, 360, fill=c, width=60)
    for x in (400, 1020):
        shadow(img, lambda m, x=x: m.rounded_rectangle([x, 520, x + 180, 860], 80, fill=255))
        d = ImageDraw.Draw(img)
        rr(d, [x, 520, x + 180, 860], 80, c)
        rr(d, [x + 30, 560, x + 150, 820], 60, shade(c, .6))
    d.arc([460, 200, 1140, 900], 180, 360, fill=c, width=60)

def cap(img, c, extra):
    shadow(img, lambda m: m.chord([440, 300, 1160, 1000], 180, 360, fill=255))
    d = ImageDraw.Draw(img)
    d.chord([440, 300, 1160, 1000], 180, 360, fill=c)
    d.ellipse([360, 560, 1400, 860], fill=shade(c, .75))
    d.chord([440, 300, 1160, 1000], 180, 360, fill=c)
    d.ellipse([780, 290, 820, 330], fill=shade(c, .7))
    if extra.get("logo"):
        d.text((680, 450), extra["logo"], fill=extra.get("logo_c", (255, 255, 255)), font_size=90)

def sneaker(img, c, extra):
    pts = [(360, 760), (440, 520), (640, 500), (760, 600), (1000, 640), (1220, 700), (1260, 820), (360, 840)]
    shadow(img, lambda m: m.polygon(pts, fill=255))
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=c)
    rr(d, [340, 810, 1280, 900], 40, extra.get("sole", (240, 240, 240)))
    for i in range(5):
        d.line([(640 + i * 50, 560 + i * 12), (700 + i * 50, 620 + i * 10)], fill=(245, 245, 245), width=10)
    if extra.get("swoosh"):
        d.arc([560, 560, 1160, 820], 20, 150, fill=extra["swoosh"], width=26)

def umbrella(img, c, extra):
    d = ImageDraw.Draw(img)
    pts = [(420, 400), (1180, 560), (1180, 640), (420, 520)]
    shadow(img, lambda m: m.polygon([(420, 380), (1260, 600), (420, 560)], fill=255))
    d = ImageDraw.Draw(img)
    d.polygon([(420, 380), (1260, 600), (420, 560)], fill=c)
    d.line([(420, 470), (1260, 600)], fill=shade(c, .7), width=8)
    d.line([(1250, 600), (1360, 620)], fill=(40, 40, 40), width=20)
    d.arc([300, 440, 460, 640], 90, 270, fill=(50, 40, 35), width=34)
    if extra.get("dots"):
        for x in range(500, 1100, 110):
            d.ellipse([x, 480, x + 34, 514], fill=extra["dots"])

def pencilcase(img, c, extra):
    shadow(img, lambda m: m.rounded_rectangle([360, 460, 1240, 840], 150, fill=255))
    d = ImageDraw.Draw(img)
    rr(d, [360, 460, 1240, 840], 150, c)
    d.line([(420, 560), (1180, 560)], fill=(60, 60, 60), width=10)
    rr(d, [1150, 540, 1260, 590], 12, (190, 190, 195))
    if extra.get("patches"):
        for i, pc in enumerate(extra["patches"]):
            d.ellipse([520 + i * 180, 640, 640 + i * 180, 760], fill=pc)

def ball(img, c, extra):
    shadow(img, lambda m: m.ellipse([480, 240, 1120, 880], fill=255))
    d = ImageDraw.Draw(img)
    if extra.get("kind") == "basketball":
        d.ellipse([480, 240, 1120, 880], fill=(214, 110, 40))
        d.line([(480, 560), (1120, 560)], fill=(40, 25, 15), width=12)
        d.line([(800, 240), (800, 880)], fill=(40, 25, 15), width=12)
        d.arc([380, 300, 700, 820], 300, 60, fill=(40, 25, 15), width=12)
        d.arc([900, 300, 1220, 820], 120, 240, fill=(40, 25, 15), width=12)
    else:
        d.ellipse([480, 240, 1120, 880], fill=(245, 245, 245))
        def pent(cx, cy, r):
            return [(cx + r * math.cos(math.radians(a - 90)), cy + r * math.sin(math.radians(a - 90))) for a in range(0, 360, 72)]
        d.polygon(pent(800, 560, 90), fill=c)
        for a in range(0, 360, 72):
            x = 800 + 230 * math.cos(math.radians(a - 90)); y = 560 + 230 * math.sin(math.radians(a - 90))
            d.polygon(pent(x, y, 70), fill=c)

def beanie(img, c, extra):
    shadow(img, lambda m: m.chord([480, 300, 1120, 1000], 180, 360, fill=255))
    d = ImageDraw.Draw(img)
    d.chord([480, 320, 1120, 1020], 180, 360, fill=c)
    rr(d, [460, 640, 1140, 800], 30, shade(c, .8))
    for x in range(500, 1120, 40):
        d.line([(x, 650), (x, 790)], fill=shade(c, .7), width=6)
    d.ellipse([720, 200, 880, 360], fill=extra.get("pom", (240, 240, 240)))

def charger(img, c, extra):
    d = ImageDraw.Draw(img)
    pts = [(560 + 160 * math.cos(t / 6) + t * 4, 560 + 200 * math.sin(t / 5)) for t in range(0, 120)]
    d.line(pts, fill=c, width=22, joint="curve")
    shadow(img, lambda m: m.rounded_rectangle([340, 420, 560, 640], 30, fill=255))
    d = ImageDraw.Draw(img)
    rr(d, [340, 420, 560, 640], 30, c)
    d.rectangle([390, 380, 410, 430], fill=(180, 180, 180)); d.rectangle([490, 380, 510, 430], fill=(180, 180, 180))
    rr(d, [1000, 470, 1120, 540], 12, (190, 190, 195))

def earbuds(img, c, extra):
    shadow(img, lambda m: m.rounded_rectangle([600, 360, 1000, 820], 120, fill=255))
    d = ImageDraw.Draw(img)
    rr(d, [600, 360, 1000, 820], 120, c)
    d.line([(600, 520), (1000, 520)], fill=shade(c, .8), width=6)
    d.ellipse([785, 640, 815, 670], fill=(120, 200, 120))
    if extra.get("skin"):
        rr(d, [600, 540, 1000, 820], 100, extra["skin"])
        d.ellipse([785, 640, 815, 670], fill=(120, 200, 120))

DRAW = dict(bottle=bottle, hoodie=hoodie, puffer=puffer, backpack=backpack, lunchbox=lunchbox, calculator=calculator,
            notebook=notebook, glasses=glasses, keys=keys, headphones=headphones, cap=cap, sneaker=sneaker,
            umbrella=umbrella, pencilcase=pencilcase, ball=ball, beanie=beanie, charger=charger, earbuds=earbuds)

def render(i, kind, color, extra, closeup=False):
    img = background(i * 7 + (3 if closeup else 0))
    DRAW[kind](img, color, extra)
    rnd = random.Random(i)
    img = img.rotate(rnd.uniform(-7, 7), resample=Image.BICUBIC, fillcolor=img.getpixel((5, 5)))
    if closeup:
        img = img.crop((W * .22, H * .22, W * .78, H * .78)).resize((W, H), Image.LANCZOS)
    img = img.resize((800, 600), Image.LANCZOS)
    # sensor noise + slight blur for a phone-photo feel
    noise = Image.effect_noise((800, 600), 10).convert("RGB")
    img = Image.blend(img, noise, .035).filter(ImageFilter.GaussianBlur(.6))
    return img

if __name__ == "__main__":
    specs = json.load(open(os.path.join(os.path.dirname(__file__), "photo_specs.json")))
    for s in specs:
        ex = {k: (tuple(v) if isinstance(v, list) and v and isinstance(v[0], int) else ([tuple(x) for x in v] if isinstance(v, list) else v)) for k, v in s.get("extra", {}).items()}
        render(s["n"], s["kind"], tuple(s["rgb"]), ex).save(os.path.join(OUT, f"p{s['n']:02d}a.jpg"), quality=84)
        if s.get("closeup"):
            render(s["n"], s["kind"], tuple(s["rgb"]), ex, closeup=True).save(os.path.join(OUT, f"p{s['n']:02d}b.jpg"), quality=84)
    print(len(os.listdir(OUT)), "photos")
