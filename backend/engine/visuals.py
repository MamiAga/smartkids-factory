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
