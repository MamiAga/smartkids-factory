"""SmartKids visual layer (Pillow, 0 TL, fully offline).

Produces per scene:
  * background card PNG (brand, progress dots, big label, subtitle, speech bubble)
  * picture sprite PNG  (Noto Color Emoji art, count rows or drawn shapes)
  * the Lumi owl sprite (original character, drawn with primitives)
and a 1280x720 thumbnail.

Every text element is checked against WCAG AA (contrast >= 4.5:1, height >= 48 px @1080p);
the numbers are returned so the quality gate can prove it (see quality.py / QUALITY_STANDARD.md).

Emoji art: Noto Color Emoji (Apache License 2.0) from the Ubuntu package fonts-noto-color-emoji.
"""
import math
import os
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI_NATIVE = 109  # the only size the CBDT bitmap font renders
MIN_CONTRAST = 4.5
MIN_TEXT_PX = 48

RGB = Tuple[int, int, int]


# --------------------------------------------------------------------------- colour maths (WCAG 2.x)
def hex_rgb(h: str) -> RGB:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def _lin(c: int) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: RGB) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: RGB, b: RGB) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def accessible_palette(bg_hex: str) -> Dict[str, Any]:
    """White text by default (darkening the bg slightly if needed); near-black only on light colours."""
    bg = hex_rgb(bg_hex)
    white, ink = (255, 255, 255), (26, 26, 26)
    if contrast(ink, bg) >= 7.0:  # light background (yellow, white, ...) -> dark text
        return {"bg": bg, "fg": ink, "contrast": round(contrast(ink, bg), 2)}
    for _ in range(60):
        if contrast(white, bg) >= MIN_CONTRAST:
            break
        bg = tuple(max(0, int(c * 0.96)) for c in bg)  # type: ignore
    return {"bg": bg, "fg": white, "contrast": round(contrast(white, bg), 2)}


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD, px)


def _fit_font(text: str, max_w: int, start: int, min_px: int = MIN_TEXT_PX) -> ImageFont.FreeTypeFont:
    px = start
    while px > min_px and _font(px).getlength(text) > max_w:
        px -= 4
    return _font(max(px, min_px))


# --------------------------------------------------------------------------- sprites
def emoji_sprite(ch: str, size: int) -> Image.Image:
    f = ImageFont.truetype(FONT_EMOJI, EMOJI_NATIVE)
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((8, 8), ch, font=f, embedded_color=True)
    bbox = canvas.getbbox()
    if not bbox:
        raise ValueError(f"emoji {ch!r} not in font")
    im = canvas.crop(bbox)
    scale = size / max(im.size)
    return im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)


def shape_sprite(shape: str, size: int, color: RGB) -> Image.Image:
    ss = 4  # supersample for smooth edges
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fill = color + (255,)
    m = int(S * 0.06)
    if shape == "circle":
        d.ellipse([m, m, S - m, S - m], fill=fill)
    elif shape == "square":
        d.rounded_rectangle([m, m, S - m, S - m], radius=int(S * 0.06), fill=fill)
    elif shape == "triangle":
        d.polygon([(S / 2, m), (S - m, S - m), (m, S - m)], fill=fill)
    elif shape == "star":
        pts = []
        for i in range(10):
            r = (S / 2 - m) if i % 2 == 0 else (S / 2 - m) * 0.45
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((S / 2 + r * math.cos(a), S / 2 + r * math.sin(a) + S * 0.03))
        d.polygon(pts, fill=fill)
    elif shape == "heart":
        r = S * 0.24
        d.ellipse([S / 2 - 2 * r + m / 2, S * 0.18, S / 2 + m / 2, S * 0.18 + 2 * r], fill=fill)
        d.ellipse([S / 2 - m / 2, S * 0.18, S / 2 + 2 * r - m / 2, S * 0.18 + 2 * r], fill=fill)
        d.polygon([(S / 2 - 2 * r + m * 0.9, S * 0.18 + r * 1.35), (S / 2 + 2 * r - m * 0.9, S * 0.18 + r * 1.35),
                   (S / 2, S - m)], fill=fill)
    else:
        raise ValueError(f"unknown shape {shape}")
    return im.resize((size, size), Image.LANCZOS)


def lumi_sprite(height: int = 300) -> Image.Image:
    """Lumi — SmartKids' own owl guide (original design, drawn from primitives)."""
    ss = 4
    w, h = int(height * 0.9) * ss, height * ss
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body, belly, wing = (126, 87, 194, 255), (209, 196, 233, 255), (94, 53, 177, 255)
    orange, white, ink = (255, 167, 38, 255), (255, 255, 255, 255), (33, 33, 33, 255)
    cx = w / 2
    # ear tufts
    d.polygon([(cx - w * 0.36, h * 0.10), (cx - w * 0.30, h * 0.30), (cx - w * 0.14, h * 0.22)], fill=wing)
    d.polygon([(cx + w * 0.36, h * 0.10), (cx + w * 0.30, h * 0.30), (cx + w * 0.14, h * 0.22)], fill=wing)
    # body + belly
    d.ellipse([cx - w * 0.40, h * 0.14, cx + w * 0.40, h * 0.94], fill=body)
    d.ellipse([cx - w * 0.25, h * 0.46, cx + w * 0.25, h * 0.90], fill=belly)
    # wings
    d.ellipse([cx - w * 0.50, h * 0.42, cx - w * 0.30, h * 0.80], fill=wing)
    d.ellipse([cx + w * 0.30, h * 0.42, cx + w * 0.50, h * 0.80], fill=wing)
    # eyes
    for sx in (-1, 1):
        ex = cx + sx * w * 0.17
        d.ellipse([ex - w * 0.15, h * 0.22, ex + w * 0.15, h * 0.49], fill=white)
        d.ellipse([ex - w * 0.075, h * 0.30, ex + w * 0.075, h * 0.44], fill=ink)
        d.ellipse([ex - w * 0.02, h * 0.315, ex + w * 0.035, h * 0.355], fill=white)
    # beak + feet
    d.polygon([(cx - w * 0.06, h * 0.47), (cx + w * 0.06, h * 0.47), (cx, h * 0.57)], fill=orange)
    for sx in (-1, 1):
        fx = cx + sx * w * 0.14
        d.ellipse([fx - w * 0.09, h * 0.90, fx + w * 0.09, h * 0.99], fill=orange)
    im = im.resize((w // ss, h // ss), Image.LANCZOS)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda a: a * 0.25))
    out = Image.new("RGBA", (im.width + 12, im.height + 12), (0, 0, 0, 0))
    out.alpha_composite(shadow, (8, 10))
    out.alpha_composite(im, (0, 0))
    return out


def picture_sprite(scene: Dict[str, Any], fg: RGB) -> Image.Image:
    pic = scene["picture"]
    if "shape" in pic:
        return shape_sprite(pic["shape"], 380, hex_rgb(pic.get("color", "FFFFFF")) if pic.get("color") else fg)
    items: List[str] = pic["emoji"]
    sizes: List[float] = pic.get("sizes") or [1.0] * len(items)
    n = len(items)
    base = 380 if n == 1 else 300 if n == 2 else 190 if n <= 5 else 150
    sprites = [emoji_sprite(e, int(base * s)) for e, s in zip(items, sizes)]
    rows = [sprites] if n <= 5 else [sprites[:5], sprites[5:]]
    gap = 36
    row_imgs = []
    for row in rows:
        rw = sum(s.width for s in row) + gap * (len(row) - 1)
        rh = max(s.height for s in row)
        r = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
        x = 0
        for s in row:
            r.alpha_composite(s, (x, rh - s.height))  # bottom-aligned (big vs small reads correctly)
            x += s.width + gap
        row_imgs.append(r)
    tw = max(r.width for r in row_imgs)
    th = sum(r.height for r in row_imgs) + gap * (len(row_imgs) - 1)
    out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    y = 0
    for r in row_imgs:
        out.alpha_composite(r, ((tw - r.width) // 2, y))
        y += r.height + gap
    return out


# --------------------------------------------------------------------------- scene card
def render_scene_assets(scene: Dict[str, Any], index: int, total: int, out_dir: str, prefix: str) -> Dict[str, Any]:
    pal = accessible_palette(scene["bg_hex"])
    bg, fg = pal["bg"], pal["fg"]
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    report: List[Dict[str, Any]] = []

    def text(xy, s, font, color, anchor, against):
        d.text(xy, s, font=font, fill=color, anchor=anchor)
        report.append({"text": s, "px": font.size, "contrast": round(contrast(color, against), 2)})

    # soft halo sized to the picture so dark/white art stays visible on any background
    pic = picture_sprite(scene, fg)
    light_bg = fg != (255, 255, 255)
    halo_rgba = (0, 0, 0, 28) if light_bg else (255, 255, 255, 60)
    hw, hh = pic.width + 140, pic.height + 110
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle([W / 2 - hw / 2, 375 - hh / 2, W / 2 + hw / 2, 375 + hh / 2],
                                           radius=min(hw, hh) // 2, fill=halo_rgba)
    im.paste(halo, (0, 0), halo)

    # brand pill + progress dots
    d.rounded_rectangle([60, 50, 380, 130], radius=40, fill=(255, 255, 255))
    text((220, 90), "SmartKids", _font(48), (26, 26, 26), "mm", (255, 255, 255))
    for i in range(total):
        cx = W - 90 - (total - 1 - i) * 56
        r = 18 if i == index else 12
        d.ellipse([cx - r, 90 - r, cx + r, 90 + r], fill=fg if i <= index else None, outline=fg, width=4)

    label_font = _fit_font(scene["label"], 1500, 170)
    text((W / 2, 745), scene["label"], label_font, fg, "mm", bg)
    if scene.get("subtitle"):
        text((W / 2, 865), scene["subtitle"], _fit_font(scene["subtitle"], 1300, 64), fg, "mm", bg)

    # speech bubble next to Lumi (bottom-left), dark text on white
    prompt = f"Can you say {scene['key']}?"
    pf = _fit_font(prompt, 900, 60)
    pw = int(pf.getlength(prompt))
    bx0, by0 = 370, 935
    d.rounded_rectangle([bx0, by0, bx0 + pw + 80, by0 + 100], radius=50, fill=(255, 255, 255))
    d.polygon([(bx0 + 10, by0 + 60), (bx0 - 40, by0 + 90), (bx0 + 40, by0 + 90)], fill=(255, 255, 255))
    text((bx0 + 40 + pw / 2, by0 + 50), prompt, pf, (26, 26, 26), "mm", (255, 255, 255))

    bg_path = os.path.join(out_dir, f"{prefix}_bg{index + 1}.png")
    im.save(bg_path)
    pic_path = os.path.join(out_dir, f"{prefix}_pic{index + 1}.png")
    pic.save(pic_path)
    return {"bg": bg_path, "picture": pic_path, "picture_size": pic.size,
            "text_checks": report, "bg_final": "%02X%02X%02X" % bg}


def render_lumi(out_dir: str, prefix: str) -> str:
    p = os.path.join(out_dir, f"{prefix}_lumi.png")
    lumi_sprite(300).save(p)
    return p


def render_thumbnail(ep: Dict[str, Any], out_path: str) -> str:
    tw, th = 1280, 720
    first = ep["scenes"][0]
    pal = accessible_palette(first["bg_hex"])
    im = Image.new("RGB", (tw, th), pal["bg"])
    d = ImageDraw.Draw(im)
    # diagonal colour stripes from the episode's scenes
    for i, sc in enumerate(ep["scenes"]):
        c = hex_rgb(sc["bg_hex"])
        x = 560 + i * 150
        d.polygon([(x, 0), (x + 150, 0), (x - 70, th), (x - 220, th)], fill=c)
    words = ep.get("thumb_text", ep["title"]).upper()
    f = _fit_font(words, 620, 120, 64)
    # white plate for guaranteed contrast
    d.rounded_rectangle([30, 40, 60 + f.getlength(words) + 40, 40 + f.size + 60], radius=36, fill=(255, 255, 255))
    d.text((70, 70), words, font=f, fill=(26, 26, 26))
    rgba = im.convert("RGBA")
    x = 640
    for sc in ep["scenes"][:3]:
        spr = picture_sprite(sc, (255, 255, 255))
        spr.thumbnail((230, 230))
        rgba.alpha_composite(spr, (x, 250 + (x // 7) % 60))
        x += 200
    lumi = lumi_sprite(330)
    rgba.alpha_composite(lumi, (60, th - lumi.height - 20))
    rgba.convert("RGB").save(out_path, "JPEG", quality=90)
    return out_path


# =========================================================================== SKQS-2 long-form layouts
NEUTRAL_BG = "29B6F6"   # sky blue for title / dance / chant / outro
DECOR = ["🌸", "🦋", "🐞", "🌼", "🐝", "🌷", "🐛", "🌻", "🍀", "🐌"]
DECOR_SPOTS = [(560, 60), (1330, 60), (70, 330), (70, 600), (1850, 330), (1850, 600), (1850, 860), (1560, 985)]


def _canvas(bg_hex: str, decor: List[str], progress: Tuple[int, int]):
    pal = accessible_palette(bg_hex)
    bg, fg = pal["bg"], pal["fg"]
    im = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(im)
    checks: List[Dict[str, Any]] = []
    # brand pill
    d.rounded_rectangle([60, 50, 380, 130], radius=40, fill=(255, 255, 255, 255))
    f = _font(48)
    d.text((220, 90), "SmartKids", font=f, fill=(26, 26, 26), anchor="mm")
    checks.append({"text": "SmartKids", "px": 48, "contrast": round(contrast((26, 26, 26), (255, 255, 255)), 2)})
    # progress dots
    done, total = progress
    if total:
        for i in range(total):
            cx = W - 90 - (total - 1 - i) * 44
            r = 15 if i == done else 10
            d.ellipse([cx - r, 90 - r, cx + r, 90 + r], fill=fg if i <= done else None, outline=fg, width=4)
    # flowers & bugs decoration
    for (x, y), e in zip(DECOR_SPOTS, decor):
        spr = emoji_sprite(e, 78)
        im.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height / 2)))
    return im, d, bg, fg, checks


def _text(d, checks, xy, s, px, color, against, max_w=1500, anchor="mm"):
    font = _fit_font(s, max_w, px)
    d.text(xy, s, font=font, fill=color, anchor=anchor)
    checks.append({"text": s, "px": font.size, "contrast": round(contrast(color, against), 2)})


def _bubble(d, checks, s):
    pf = _fit_font(s, 1000, 60)
    pw = int(pf.getlength(s))
    bx0, by0 = 370, 935
    d.rounded_rectangle([bx0, by0, bx0 + pw + 80, by0 + 100], radius=50, fill=(255, 255, 255))
    d.polygon([(bx0 + 10, by0 + 60), (bx0 - 40, by0 + 90), (bx0 + 40, by0 + 90)], fill=(255, 255, 255))
    d.text((bx0 + 40 + pw / 2, by0 + 50), s, font=pf, fill=(26, 26, 26), anchor="mm")
    checks.append({"text": s, "px": pf.size, "contrast": round(contrast((26, 26, 26), (255, 255, 255)), 2)})


def _row(emojis: List[str], size: int, gap: int = 30, highlight: int = -1) -> Image.Image:
    sprites = []
    for i, e in enumerate(emojis):
        s = emoji_sprite(e, int(size * (1.35 if i == highlight else 1.0)))
        if i == highlight:
            ring = Image.new("RGBA", (s.width + 40, s.height + 40), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([0, 0, ring.width - 1, ring.height - 1], fill=(255, 255, 255, 150))
            ring.alpha_composite(s, (20, 20))
            s = ring
        sprites.append(s)
    w = sum(s.width for s in sprites) + gap * (len(sprites) - 1)
    h = max(s.height for s in sprites)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for s in sprites:
        out.alpha_composite(s, (x, (h - s.height) // 2))
        x += s.width + gap
    return out


def _tiles(emojis: List[str], correct: int = -1, dim_wrong: bool = False) -> Image.Image:
    tile, gap = 340, 70
    out = Image.new("RGBA", (tile * 3 + gap * 2 + 40, tile + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    for i, e in enumerate(emojis):
        x = 20 + i * (tile + gap)
        good = i == correct
        d.rounded_rectangle([x, 20, x + tile, 20 + tile], radius=48,
                            fill=(255, 255, 255, 255 if not (dim_wrong and not good) else 110),
                            outline=(46, 125, 50, 255) if good else None, width=16 if good else 0)
        s = emoji_sprite(e, 240)
        if dim_wrong and not good:
            s.putalpha(s.getchannel("A").point(lambda a: a * 0.35))
        out.alpha_composite(s, (x + (tile - s.width) // 2, 20 + (tile - s.height) // 2))
        if good:
            st = emoji_sprite("⭐", 110)
            out.alpha_composite(st, (x + tile - 90, 0))
    return out


def _badge(n: int) -> Image.Image:
    im = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([10, 10, 250, 250], fill=(255, 255, 255, 255), outline=(255, 179, 0, 255), width=14)
    d.text((130, 138), str(n), font=_font(170), fill=(26, 26, 26), anchor="mm")
    return im


def render_segment(pack: Dict[str, Any], v: Dict[str, Any], out_dir: str, prefix: str, seq: int,
                   decor: List[str]) -> Dict[str, Any]:
    """Return {"frames": [{"bg": png, "hero": png, "hero_y": int}], "text_checks": [...], "has_picture": bool}.
    Countdown segments return 3 frames (3, 2, 1)."""
    items = pack["items"]
    kind = v["kind"]
    it = items[v["item"]] if "item" in v else None
    bg_hex = it["bg_hex"] if it else NEUTRAL_BG
    progress = (v["item"], len(items)) if it else (0, 0)
    frames, checks_all = [], []

    def finish(im, hero, hero_y=375, tag=""):
        p_bg = os.path.join(out_dir, f"{prefix}_{seq:03d}{tag}_bg.png")
        p_hero = os.path.join(out_dir, f"{prefix}_{seq:03d}{tag}_hero.png")
        im.convert("RGB").save(p_bg)
        hero.save(p_hero)
        frames.append({"bg": p_bg, "hero": p_hero, "hero_y": hero_y})

    noun = pack["noun"]
    if kind == "countdown":
        for n in (3, 2, 1):
            im, d, bg, fg, ch = _canvas(bg_hex, decor, progress)
            style = v.get("style")
            if style == "mystery":
                hero = _badge(n)
                _text(d, ch, (W / 2, 745), f"Guess the next {noun}!", 110, fg, bg)
            elif style == "quiz":
                hero = _tiles(v["choices"])
                _text(d, ch, (W / 2, 690), f"Which one is {it['key']}?", 96, fg, bg)
                b = _badge(n)
                im.alpha_composite(b.resize((190, 190)), (W // 2 - 95, 790))
            else:  # review
                hero = emoji_sprite(it["pic"], 360)
                b = _badge(n)
                im.alpha_composite(b.resize((190, 190)), (W // 2 - 95, 700))
            _bubble(d, ch, f"{n}...")
            checks_all += ch
            finish(im, hero, 330 if style == "quiz" else 375, tag=f"_{n}")
        return {"frames": frames, "text_checks": checks_all, "has_picture": True}

    im, d, bg, fg, ch = _canvas(bg_hex, decor, progress)
    hero_y = 375
    if kind == "title":
        hero = _row([i["pic"] for i in items], 150, 24)
        _text(d, ch, (W / 2, 745), v.get("title", pack["thumb_text"]), 140, fg, bg)
        _bubble(d, ch, "Let's learn and play!")
    elif kind == "mystery":
        hero = emoji_sprite("❓", 330)
        _text(d, ch, (W / 2, 745), f"Guess the next {noun}!", 110, fg, bg)
        _bubble(d, ch, "Get ready!")
    elif kind in ("reveal", "repeat"):
        hero = emoji_sprite(it["pic"], 380)
        _text(d, ch, (W / 2, 745), it["label"], 170, fg, bg)
        if it.get("phrase") and pack["family"] == "colors":
            _text(d, ch, (W / 2, 862), it["phrase"].capitalize(), 64, fg, bg, max_w=1300)
        _bubble(d, ch, f"Can you say {it['key']}?" if kind == "repeat" else f"It's {it['key']}!")
    elif kind == "example":
        hero = emoji_sprite(v["emoji"], 360)
        _text(d, ch, (W / 2, 745), v["caption"].capitalize() if pack["family"] == "colors" else it["label"], 130, fg, bg)
        if pack["family"] == "colors":
            _text(d, ch, (W / 2, 862), f"is {it['key']}!", 72, fg, bg)
        _bubble(d, ch, f"{it['label'].title()}!")
    elif kind in ("quiz", "answer"):
        hero = _tiles(v["choices"], correct=v.get("correct", -1), dim_wrong=kind == "answer")
        hero_y = 330
        q = f"Which one is {it['key']}?" if pack["family"] == "colors" else f"Which one is the {it['key']}?"
        _text(d, ch, (W / 2, 690), q, 96, fg, bg)
        _bubble(d, ch, "Guess!" if kind == "quiz" else "Yes! Great job!")
    elif kind in ("review", "review_answer"):
        hero = emoji_sprite(it["pic"], 380)
        if kind == "review_answer":
            _text(d, ch, (W / 2, 745), it["label"], 170, fg, bg)
            _bubble(d, ch, "You got it!")
        else:
            _text(d, ch, (W / 2, 745), f"What {noun} is this?", 110, fg, bg)
            _bubble(d, ch, "Shout it out!")
    elif kind in ("chant", "chant_intro"):
        hl = v.get("item", -1) if kind == "chant" else -1
        hero = _row([i["pic"] for i in items], 140, 24, highlight=hl)
        _text(d, ch, (W / 2, 745), items[hl]["label"] if hl >= 0 else "Sing along!", 150, fg, bg)
        _bubble(d, ch, "Sing with me!")
    elif kind == "dance":
        hero = _row(["💃", "🕺", "🎵", "👏"], 220, 50)
        _text(d, ch, (W / 2, 745), "Dance break!", 150, fg, bg)
        _bubble(d, ch, "Wiggle and clap!")
    elif kind == "outro":
        hero = _row([i["pic"] for i in items], 150, 24)
        _text(d, ch, (W / 2, 745), "Great job!", 160, fg, bg)
        _bubble(d, ch, "See you next time!")
    else:
        raise ValueError(kind)
    checks_all += ch
    finish(im, hero, hero_y)
    return {"frames": frames, "text_checks": checks_all, "has_picture": True}


def render_longform_thumbnail(pack: Dict[str, Any], out_path: str) -> str:
    tw, th = 1280, 720
    im = Image.new("RGBA", (tw, th), hex_rgb("FFF59D") + (255,))
    d = ImageDraw.Draw(im)
    cols = [hex_rgb(i["bg_hex"]) for i in pack["items"]]
    for i, c in enumerate(cols):   # rainbow sunburst
        a0, a1 = i * 360 / len(cols), (i + 1) * 360 / len(cols)
        d.pieslice([-400, -500, tw + 400, th + 700], a0, a1, fill=c + (255,))
    d.ellipse([tw / 2 - 330, th / 2 - 250, tw / 2 + 330, th / 2 + 330], fill=(255, 255, 255, 235))
    words = pack["thumb_text"].upper()
    f = _fit_font(words, 1150, 130, 64)
    x0 = tw / 2 - f.getlength(words) / 2
    d.rounded_rectangle([x0 - 30, 30, x0 + f.getlength(words) + 30, 30 + f.size + 50], radius=40, fill=(255, 255, 255, 255),
                        outline=(26, 26, 26, 255), width=6)
    d.text((tw / 2, 30 + (f.size + 50) / 2), words, font=f, fill=(26, 26, 26), anchor="mm")
    row = _row([i["pic"] for i in pack["items"][:4]], 170, 20)
    im.alpha_composite(row, (int(tw / 2 - row.width / 2), 300))
    for (x, y), e in zip([(70, 640), (1210, 640), (1210, 260), (70, 260), (640, 660)], DECOR):
        s = emoji_sprite(e, 100)
        im.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
    lumi = lumi_sprite(300)
    im.alpha_composite(lumi, (20, th - lumi.height))
    im.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
