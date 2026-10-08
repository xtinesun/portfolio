#!/usr/bin/env python3
"""CS2 project-card preview — symbolic email A | B, then B dims.

Top strip matches CS1 browser chrome grey. Text + text bars use greys/blacks.
Icons use CS1 circular badge tints. CTA keeps rose; video play is grey.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent
OUT_CARD = ASSETS / "cs2-project-card.gif"
OUT_HERO = ASSETS / "cs2-hero-card.gif"
OUT_POSTER = ASSETS / "cs2-project-card-poster.png"

# Master render at 2× so case-study headers stay crisp on retina (~1140 CSS px)
HERO_W, HERO_H = 2160, 1350
CARD_W, CARD_H = 1080, 675
W, H = HERO_W, HERO_H

# CS2 pink wash (AA fringe / poster only)
GRAD_TOP = (249, 141, 176)
GRAD_MID = (246, 158, 174)
GRAD_BOT = (241, 181, 180)

# Light browser chrome (lighter than CS1 #e3e3e3 sample)
BROWSER_TOP = (238, 238, 238)

# Accent — CTA keeps rose; list-row icons use CS1 badge tints; play is grey
ACCENT = (155, 72, 108)
CTA = (155, 72, 108)
CHIP_VIDEO = (139, 92, 246)   # CS1 Video clip #8b5cf6
CHIP_MAIL = (224, 121, 74)    # CS1 email chip #e0794a
PLAY = (150, 150, 154)        # play control — slightly darker grey on light video box
MAIL_BG = (255, 232, 238)
MAIL_FG = (155, 72, 108)
PLACEHOLDER = (242, 242, 243)  # video block — very light grey
BTN = CTA
CANVAS = (255, 255, 255)

# Greys / blacks for text + symbolic text bars
INK = (42, 42, 45)       # headlines
INK_2 = (140, 140, 145)  # body bars
LINE = (228, 228, 230)   # card outline
BADGE = INK

BTN_W = 132
BTN_H = 32


def load_font(size: int, bold: bool = False):
    fonts_dir = ROOT / "fonts"
    names = (
        (
            str(fonts_dir / ("PlusJakartaSans-Bold-static.ttf" if bold else "PlusJakartaSans-Regular.ttf")),
            None,
        ),
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
            None,
        ),
        ("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
    )
    for path, idx in names:
        try:
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size=size, index=idx or 0)
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_in_out(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def make_gradient(w: int, h: int) -> Image.Image:
    yy = np.linspace(0.0, 1.0, h, dtype=np.float64)[:, None]
    xx = np.linspace(0.0, 1.0, w, dtype=np.float64)[None, :]
    c0 = np.array(GRAD_TOP, dtype=np.float64)
    c1 = np.array(GRAD_MID, dtype=np.float64)
    c2 = np.array(GRAD_BOT, dtype=np.float64)
    t = yy
    u1 = np.clip(t / 0.45, 0.0, 1.0)
    u2 = np.clip((t - 0.45) / 0.55, 0.0, 1.0)
    u1s = u1 * u1 * (3.0 - 2.0 * u1)
    u2s = u2 * u2 * (3.0 - 2.0 * u2)
    top_mid = c0 * (1 - u1s[..., None]) + c1 * u1s[..., None]
    mid_bot = c1 * (1 - u2s[..., None]) + c2 * u2s[..., None]
    rgb = np.where((t > 0.45)[..., None], mid_bot, top_mid)
    bloom_r = np.sqrt(((xx - 0.5) / 0.6) ** 2 + ((yy - 0.12) / 0.45) ** 2)
    bloom = np.clip(1.0 - bloom_r, 0.0, 1.0) ** 1.35
    rgb = rgb + (255.0 - rgb) * (bloom[..., None] * 0.26)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")


def round_rect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def draw_text_lines(d, x, y, widths, full_w, color=INK_2, h=7, gap=8):
    for frac in widths:
        lw = max(8, int(full_w * frac))
        round_rect(d, (x, y, x + lw, y + h), 3, fill=color)
        y += h + gap
    return y


def draw_image_block(d, box, scale: float = 1.0):
    """Video placeholder — soft rose fill + play (keep accent color)."""
    x0, y0, x1, y1 = box
    round_rect(d, box, max(6, int(round(10 * scale))), fill=PLACEHOLDER)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = max(10, int(round(14 * scale)))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PLAY)
    d.polygon(
        [
            (cx - r * 0.2, cy - r * 0.4),
            (cx - r * 0.2, cy + r * 0.4),
            (cx + r * 0.5, cy),
        ],
        fill=(255, 255, 255),
    )


def draw_chip_icon(d, box, tint, glyph="mail"):
    """Circular badge icons — same shape language as CS1 hero chips."""
    x0, y0, x1, y1 = box
    d.ellipse((x0, y0, x1, y1), fill=tint)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = min(x1 - x0, y1 - y0) * 0.18
    w = (255, 255, 255)
    if glyph == "mail":
        d.rounded_rectangle((cx - s * 1.4, cy - s, cx + s * 1.4, cy + s), radius=2, outline=w, width=2)
        d.line((cx - s * 1.2, cy - s * 0.5, cx, cy + s * 0.3, cx + s * 1.2, cy - s * 0.5), fill=w, width=2)
    elif glyph == "video":
        d.rounded_rectangle((cx - s * 1.3, cy - s, cx + s * 1.3, cy + s), radius=2, outline=w, width=2)
        d.polygon([(cx - s * 0.2, cy - s * 0.55), (cx - s * 0.2, cy + s * 0.55), (cx + s * 0.7, cy)], fill=w)
    else:
        d.rounded_rectangle((cx - s * 1.2, cy - s * 1.1, cx + s * 1.2, cy + s * 1.1), radius=2, outline=w, width=2)
        d.line((cx - s * 0.7, cy - s * 0.2, cx + s * 0.7, cy - s * 0.2), fill=w, width=2)


def draw_badge(card: Image.Image, cx: float, cy: float, letter: str, diam: int = 33):
    r = diam // 2
    bx, by = int(round(cx)), int(round(cy))
    d = ImageDraw.Draw(card)
    stroke = max(2, diam // 16)
    d.ellipse((bx - r, by - r, bx + r, by + r), outline=INK, width=stroke)

    scale = 3
    big_d = diam * scale
    big_r = (big_d - 1) / 2
    big_fnt = load_font(max(12, int(round(diam * 0.45))) * scale, bold=True)
    scratch = Image.new("L", (big_d, big_d), 0)
    ImageDraw.Draw(scratch).text((big_r, big_r), letter, font=big_fnt, fill=255, anchor="mm")
    arr = np.array(scratch)
    ys, xs = np.where(arr >= 200)
    if len(xs) == 0:
        return
    dx = big_r - xs.mean()
    dy = big_r - ys.mean()
    glyph = Image.new("RGBA", (big_d, big_d), (0, 0, 0, 0))
    ImageDraw.Draw(glyph).text(
        (big_r + dx, big_r + dy), letter, font=big_fnt, fill=(*INK, 255), anchor="mm"
    )
    small = glyph.resize((diam, diam), Image.Resampling.LANCZOS)
    card.alpha_composite(small, (bx - r, by - r))


def draw_button(d, cx: float, y: float, fill: tuple[int, int, int], label: str = "", scale: float = 1.0):
    bw = max(48, int(round(BTN_W * scale)))
    bh = max(18, int(round(BTN_H * scale)))
    x0 = int(round(cx - bw / 2))
    x1 = x0 + bw
    y1 = y + bh
    r = bh // 2
    round_rect(d, (x0, y, x1, y1), r, fill=fill)
    if label:
        fnt = load_font(max(10, int(round(13 * scale))), bold=True)
        d.text((cx, y + bh / 2 - 0.5), label, font=fnt, fill=(255, 255, 255), anchor="mm")
    return y + bh


def draw_headline(d, x0, x1, y, lines, color=INK, scale: float = 1.0):
    fnt = load_font(max(12, int(round(16 * scale))), bold=True)
    line_h = max(16, int(round(20 * scale)))
    for i, line in enumerate(lines):
        d.text((x0, y + i * line_h), line, font=fnt, fill=color)
    return y + len(lines) * line_h


def draw_email(size: tuple[int, int], variant: str) -> Image.Image:
    w, h = size
    is_a = variant == "A"
    sc = w / 300.0
    # Slightly rounder than CS1 window ratio for readable corners at card size
    CARD_R = max(6, int(round(w * 0.022)))
    STRIP = max(12, int(round(18 * sc)))

    # Grey fills the whole card first so top corners stay chrome (never white).
    # White starts at STRIP with a hard edge — no darker divider line.
    layer = Image.new("RGBA", (w, h), (*BROWSER_TOP, 255))
    ld = ImageDraw.Draw(layer)
    ld.rectangle([0, STRIP, w, h], fill=(*CANVAS, 255))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=CARD_R, fill=255)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.paste(layer, (0, 0), mask)
    d = ImageDraw.Draw(img)

    PAD = max(12, int(round(24 * sc)))
    GAP_XS = max(4, int(round(6 * sc)))
    GAP_SM = max(6, int(round(10 * sc)))
    GAP_MD = max(8, int(round(16 * sc)))
    GAP_LG = max(12, int(round(22 * sc)))
    bar_h = max(4, int(round(5 * sc)))

    x0, x1 = PAD, w - PAD
    content_w = x1 - x0
    media_h = int(content_w * 0.36)

    y = STRIP + max(16, int(round(28 * sc)))
    br = max(10, int(round(14 * sc)))
    bx = (x0 + x1) / 2
    by = y + br
    draw_badge(img, bx, by, variant, diam=max(24, int(round(33 * sc))))
    y += br * 2 + GAP_LG + max(2, int(round(4 * sc)))

    headline = ["Your new course is ready"]
    cta_label = "Watch now"
    body = [0.90, 0.84, 0.58]

    y = draw_headline(d, x0, x1, y, headline, INK, scale=sc)
    y += GAP_SM
    y = draw_text_lines(d, x0, y, body, content_w, color=INK_2, h=bar_h, gap=GAP_XS)
    y += GAP_LG

    if is_a:
        draw_image_block(d, (x0, y, x1, y + media_h), scale=sc)
        y += media_h + GAP_MD
        y = draw_button(d, (x0 + x1) / 2, y, CTA, cta_label, scale=sc)
        y += GAP_LG

        thumb = max(24, int(round(36 * sc)))
        chips = ((CHIP_VIDEO, "video"), (CHIP_MAIL, "mail"))
        row_gap = GAP_MD
        for i, (tint, glyph) in enumerate(chips):
            if y + thumb > h - PAD:
                break
            text_w = content_w - thumb - GAP_SM
            text_y = y + (thumb - (bar_h + GAP_XS + bar_h)) // 2
            if i % 2 == 0:
                draw_chip_icon(d, (x0, y, x0 + thumb, y + thumb), tint, glyph)
                draw_text_lines(d, x0 + thumb + GAP_SM, text_y, [0.72, 0.48], text_w, color=INK_2, h=bar_h, gap=GAP_XS)
            else:
                draw_text_lines(d, x0, text_y, [0.72, 0.48], text_w, color=INK_2, h=bar_h, gap=GAP_XS)
                draw_chip_icon(d, (x1 - thumb, y, x1, y + thumb), tint, glyph)
            y += thumb + row_gap
    else:
        dot = max(4, int(round(6 * sc)))
        for frac in (0.72, 0.66, 0.70):
            d.ellipse((x0 + 1, y + 1, x0 + dot, y + dot), fill=INK_2)
            round_rect(
                d,
                (x0 + 12, y + 1, x0 + 12 + int(content_w * frac), y + bar_h + 1),
                2,
                fill=INK_2,
            )
            y += bar_h + GAP_SM
        y += GAP_MD

        draw_image_block(d, (x0, y, x1, y + media_h), scale=sc)
        y += media_h + GAP_MD
        draw_button(d, (x0 + x1) / 2, y, CTA, cta_label, scale=sc)

    # Re-stamp chrome band only (no darker under-line)
    strip_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strip_layer)
    sd.rectangle([0, 0, w, STRIP], fill=(*BROWSER_TOP, 255))
    strip_clip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    strip_clip.paste(strip_layer, (0, 0), mask)
    img.alpha_composite(strip_clip)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=CARD_R, outline=LINE, width=max(1, int(round(sc))))

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def paste_scaled_rot(dst, src, cx, cy, scale, rotate=0.0, opacity=1.0):
    if scale <= 0.01 or opacity <= 0.01:
        return
    w, h = src.size
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    piece = src.resize((nw, nh), Image.Resampling.LANCZOS)
    if abs(rotate) > 0.05:
        piece = piece.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=True)
    if opacity < 0.999:
        a = piece.split()[-1].point(lambda p: int(p * opacity))
        piece.putalpha(a)
    pw, ph = piece.size
    dst.alpha_composite(piece, (int(round(cx - pw / 2)), int(round(cy - ph / 2))))


def draw_sparkle(layer, x, y, size, alpha):
    if alpha < 0.04 or size < 0.8:
        return
    a = int(255 * clamp01(alpha))
    fill = (255, 252, 250, a)
    d = ImageDraw.Draw(layer)
    cx, cy, s = x, y, size
    tip = 0.20
    d.polygon([(cx, cy - s), (cx + s * tip, cy), (cx, cy + s), (cx - s * tip, cy)], fill=fill)
    d.polygon([(cx - s, cy), (cx, cy - s * tip), (cx + s, cy), (cx, cy + s * tip)], fill=fill)
    r = max(1.2, s * 0.22)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, a))


def sparkle_flash(t, period, phase, duty=0.28):
    u = (t / period + phase) % 1.0
    if u > duty:
        return 0.0
    local = u / duty
    if local < 0.18:
        return local / 0.18
    return ((1.0 - local) / 0.82) ** 1.25


def draw_a_sparkles(frame, card_x, card_y, strength, t, scale: float = 1.0):
    if strength < 0.08:
        return
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    pos = {
        "a": (-14 * scale, 26 * scale, 17.0 * scale),
        "b": (32 * scale, -14 * scale, 14.5 * scale),
        "c": (-12 * scale, -12 * scale, 12.5 * scale),
        "d": (16 * scale, -20 * scale, 10.0 * scale),
        "e": (4 * scale, 18 * scale, 9.0 * scale),
    }
    period = 1.15
    schedule = (
        ("a", period, 0.00, 0.14),
        ("b", period, 0.22, 0.15),
        ("c", period, 0.24, 0.14),
        ("d", period, 0.44, 0.13),
        ("a", period, 0.64, 0.15),
        ("e", period, 0.66, 0.14),
        ("c", period, 0.86, 0.13),
    )
    for key, per, phase, duty in schedule:
        ox, oy, size = pos[key]
        flash = sparkle_flash(t, per, phase, duty)
        if flash < 0.05:
            continue
        jx = 1.6 * scale * math.sin(phase * 17.0 + t * 1.1)
        jy = 1.2 * scale * math.cos(phase * 11.0 + t * 0.9) - 2.0 * scale * flash
        draw_sparkle(
            layer,
            card_x + ox + jx,
            card_y + oy + jy,
            size * (0.5 + 0.6 * flash),
            strength * (0.4 + 0.6 * flash),
        )
    frame.alpha_composite(layer)


def hero_float(t, delay=0.0, amp=4.0, period=7.0):
    phase = ((t + delay) % period) / period
    wave = 0.5 - 0.5 * math.cos(phase * 2.0 * math.pi)
    return -amp * wave, -0.35 + 0.7 * wave


_EMAIL_CACHE = {}


def get_emails(ew, eh):
    key = (ew, eh)
    if key not in _EMAIL_CACHE:
        _EMAIL_CACHE[key] = (draw_email((ew, eh), "A"), draw_email((ew, eh), "B"))
    return _EMAIL_CACHE[key]


def compose(t, bg):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = W / 1080.0
    ew, eh = int(round(300 * s)), int(round(480 * s))
    gap = int(round(40 * s))
    total_w = ew * 2 + gap
    left = (W - total_w) // 2
    top = (H - eh) // 2 + int(round(6 * s))

    email_a, email_b = get_emails(ew, eh)

    dim_start, dim_dur = 1.35, 0.95
    reset_start, reset_dur = 4.35, 0.95
    dim_fwd = ease_in_out(clamp01((t - dim_start) / dim_dur))
    reset = ease_in_out(clamp01((t - reset_start) / reset_dur))
    dim = dim_fwd * (1.0 - reset)

    b_opacity = 1.0 - 0.55 * dim
    a_scale = 1.0 + 0.09 * dim

    ay, arot_live = hero_float(t, delay=0.25, amp=4.0 * s, period=7.0)
    # No tilt while A and B are the same size (rotate shimmer reads as a slight lean).
    # Soft tilt only as A scales up as the winner.
    tilt_gate = ease_in_out(clamp01((dim - 0.08) / 0.4))
    arot = arot_live * tilt_gate * 0.25
    if dim < 0.04:
        by, _ = hero_float(t, delay=1.4, amp=4.0 * s, period=7.0)
        brot = 0.0
    else:
        settle = ease_in_out(clamp01(dim / 0.45))
        by_live, _ = hero_float(t, delay=1.4, amp=4.0 * s, period=7.0)
        by = by_live * (1.0 - settle)
        brot = 0.0

    ax_cx = left + ew / 2
    ay_cy = top + eh / 2 + ay
    bx0 = left + ew + gap
    bx_cx = bx0 + ew / 2
    by_cy = top + eh / 2 + by

    paste_scaled_rot(frame, email_a, ax_cx, ay_cy, a_scale, rotate=arot)

    if dim > 0.08 and t >= dim_start + 0.38:
        card_x = ax_cx - (ew * a_scale) / 2
        card_y = ay_cy - (eh * a_scale) / 2
        # Short beat after A wins / B dims, then sparkles; stay snappy on a faster clock
        sparkle_in = ease_in_out(clamp01((t - dim_start - 0.38) / 0.18))
        sparkle_t = dim_start + 0.38 + (t - dim_start - 0.38) * 2.1
        draw_a_sparkles(frame, card_x, card_y, dim * sparkle_in, sparkle_t, scale=s)

    if b_opacity < 0.999:
        b = email_b.copy()
        # Dim veil clipped to the same rounded silhouette as the email
        # (including the grey top bar corners) so corners don't go oddly opaque.
        veil = Image.new("RGBA", (ew, eh), (0, 0, 0, 0))
        vd = ImageDraw.Draw(veil)
        vd.rounded_rectangle(
            (0, 0, ew - 1, eh - 1),
            radius=max(6, int(round(ew * 0.022))),
            fill=(120, 50, 75, int(55 * dim)),
        )
        b = Image.alpha_composite(b, veil)
        a = b.split()[-1].point(lambda p: int(p * b_opacity))
        b.putalpha(a)
        paste_scaled_rot(frame, b, bx_cx, by_cy, 1.0, rotate=brot)
    else:
        paste_scaled_rot(frame, email_b, bx_cx, by_cy, 1.0, rotate=brot)

    return frame


def quantize_rgba_frames(rgba_frames, colors=180):
    flat_frames = []
    empty_masks = []
    white_masks = []
    for fr in rgba_frames:
        rgba = fr.convert("RGBA")
        alpha = np.array(rgba.getchannel("A"))
        rgb_arr = np.array(rgba)
        # Track true email/canvas white before pink wash composites into the palette
        white_masks.append(
            (alpha >= 250)
            & (rgb_arr[:, :, 0] >= 254)
            & (rgb_arr[:, :, 1] >= 254)
            & (rgb_arr[:, :, 2] >= 254)
        )
        solid = Image.new("RGBA", rgba.size, (*GRAD_MID, 255))
        flat = Image.alpha_composite(solid, rgba)
        flat_frames.append(flat.convert("RGB"))
        empty_masks.append(alpha < 12)

    idxs = sorted({0, len(flat_frames) // 3, (2 * len(flat_frames)) // 3, len(flat_frames) - 1})
    samples = []
    for idx in idxs:
        arr = np.array(flat_frames[idx])
        keep = ~empty_masks[idx]
        if keep.any():
            samples.append(arr[keep])
    pix = np.concatenate(samples, axis=0)
    if len(pix) > 60000:
        pix = pix[:: len(pix) // 60000]
    sheet = Image.fromarray(pix.reshape(-1, 1, 3).repeat(3, axis=1), "RGB")
    seeds = [
        GRAD_TOP, GRAD_MID, GRAD_BOT, BROWSER_TOP, CANVAS, PLACEHOLDER,
        ACCENT, CTA, CHIP_VIDEO, CHIP_MAIL, PLAY, INK, INK_2, LINE, MAIL_BG, MAIL_FG,
        (255, 255, 255), (255, 255, 255), (255, 255, 255), (255, 255, 255),
        (238, 238, 238), (238, 238, 238), (238, 238, 238),
    ]
    sw = Image.new("RGB", (len(seeds) * 10, 10), (255, 255, 255))
    sd = ImageDraw.Draw(sw)
    for i, col in enumerate(seeds):
        sd.rectangle((i * 10, 0, i * 10 + 9, 9), fill=col)
    pad = Image.new("RGB", (max(sheet.width, sw.width), sheet.height + 14), (255, 255, 255))
    pad.paste(sheet, (0, 0))
    pad.paste(sw, (0, sheet.height + 2))
    master = pad.quantize(colors=max(8, colors - 1), method=Image.Quantize.MAXCOVERAGE)

    frames = []
    for rgb, empty, is_white in zip(flat_frames, empty_masks, white_masks):
        # Lock email bodies to pure white before palette mapping
        arr = np.array(rgb)
        arr[is_white] = CANVAS
        rgb = Image.fromarray(arr, "RGB")
        q = rgb.quantize(palette=master, dither=Image.Dither.NONE)
        pal = (q.getpalette() or []) + [0] * 768
        pal = pal[:768]
        # Force every near-white palette slot to exact white (kills pink wash bleed)
        for i in range(256):
            r, g, b = pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]
            if r >= 248 and g >= 248 and b >= 248:
                pal[i * 3 : i * 3 + 3] = [255, 255, 255]
            # Lock browser chrome grey
            elif abs(r - 238) <= 4 and abs(g - 238) <= 4 and abs(b - 238) <= 4:
                pal[i * 3 : i * 3 + 3] = list(BROWSER_TOP)
        pal[765:768] = list(GRAD_MID)
        pix = np.array(q, dtype=np.uint8)
        pix[empty] = 255
        out = Image.fromarray(pix, mode="P")
        out.putpalette(pal)
        out.info["transparency"] = 255
        frames.append(out)
    return frames


def build():
    global W, H
    W, H = HERO_W, HERO_H
    _EMAIL_CACHE.clear()

    bg = make_gradient(W, H)
    # Denser samples so sparkles stay fluid while motion is slower overall
    dt = 0.05
    # Reset finishes ~5.3s; hold peer-sized A|B before looping
    key_times = [round(i * dt, 3) for i in range(0, int(6.5 / dt) + 1)]

    durations = []
    for i, t in enumerate(key_times):
        if i + 1 < len(key_times):
            durations.append(max(50, int(round((key_times[i + 1] - t) * 1000))))
        else:
            durations.append(900)  # pause before restart

    frames_rgba = [compose(t, bg) for t in key_times]
    poster = bg.copy()
    poster.alpha_composite(frames_rgba[len(frames_rgba) // 2])
    poster.convert("RGB").save(OUT_POSTER, "PNG", optimize=True)

    # High-res header (2×) — richer palette for crisp case-study display
    hero_frames = quantize_rgba_frames(frames_rgba, colors=220)
    hero_frames[0].save(
        OUT_HERO,
        save_all=True,
        append_images=hero_frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
        transparency=255,
    )

    # Homepage card — downscale from master for lighter weight
    card_rgba = [
        fr.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS) for fr in frames_rgba
    ]
    card_frames = quantize_rgba_frames(card_rgba, colors=180)
    card_frames[0].save(
        OUT_CARD,
        save_all=True,
        append_images=card_frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
        transparency=255,
    )
    total = sum(durations) / 1000
    print(f"Wrote {OUT_HERO.name} ({OUT_HERO.stat().st_size / 1024:.0f} KB) {HERO_W}x{HERO_H}, {len(hero_frames)} frames, {total:.1f}s")
    print(f"Wrote {OUT_CARD.name} ({OUT_CARD.stat().st_size / 1024:.0f} KB) {CARD_W}x{CARD_H}, {len(card_frames)} frames, {total:.1f}s")


if __name__ == "__main__":
    build()
