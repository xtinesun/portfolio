#!/usr/bin/env python3
"""CS3 preview/hero GIF from the provided Automations UI parts.

Special animation: trigger pops in → dashed line draws → plus pulses/spins →
action cards spawn (email, SMS, offer) → End slides down. Teal→green gradient.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "parts"
OUT_GIF = ROOT.parent / "cs3-hero-flow.gif"
OUT_POSTER = ROOT.parent / "cs3-hero-flow-poster.png"
OUT_CARD = ROOT.parent / "cs3-project-card.gif"
BG_PNG = ROOT.parent / "cs3-gradient-bg.jpg"
if not BG_PNG.exists():
    BG_PNG = ROOT.parent / "cs3-gradient-bg.png"

W, H = 1920, 1080
CARD_W, CARD_H = 1440, 900
# Match CS1/CS2 case-hero aspect (1024 / 470)
HERO_ASPECT = 1024 / 470
HERO_W = 1440
HERO_H = int(round(HERO_W / HERO_ASPECT))  # ~661

# Fallback stops if the PNG is missing (match uploaded cyan→mint)
GRAD_TOP = (90, 204, 228)    # #5acce4
GRAD_MID = (116, 215, 211)   # #74d7d3
GRAD_BOT = (149, 227, 187)   # #95e3bb

WHITE = (255, 255, 255)
TEXT = (55, 60, 68)
SHADOW = (60, 40, 90)  # match CS1 hero-window shadow tint
DASH = (180, 184, 190)
CANVAS = (244, 245, 247)
DOT = (220, 222, 226)
# Match CS2 sparkle fill (warm near-white)
SPARK = (255, 252, 250)


def load_font(size: int, bold: bool = False):
    for path in (
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size=size, index=1 if bold else 0)
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c0, c1, t: float):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c0, c1))


def ease_out_cubic(t: float) -> float:
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t: float, overshoot: float = 1.7) -> float:
    t = clamp01(t)
    return 1 + (overshoot + 1) * (t - 1) ** 3 + overshoot * (t - 1) ** 2


def ease_in_out(t: float) -> float:
    t = clamp01(t)
    return 3 * t * t - 2 * t * t * t


def progress(t: float, start: float, dur: float, fn=ease_out_cubic) -> float:
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return fn(clamp01((t - start) / dur))


def make_gradient(w: int, h: int) -> Image.Image:
    """Full-bleed background from the uploaded PNG (scaled to cover).

    Uses the actual image pixels — not a color-sampled recreation.
    """
    if BG_PNG.exists():
        src = Image.open(BG_PNG).convert("RGB")
        sw, sh = src.size
        # Cover: scale so the PNG fills the target, then center-crop
        scale = max(w / sw, h / sh)
        nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
        # High-quality upsample; source is smaller than hero so LANCZOS softens
        scaled = src.resize((nw, nh), Image.Resampling.LANCZOS)
        x0 = (nw - w) // 2
        y0 = (nh - h) // 2
        cropped = scaled.crop((x0, y0, x0 + w, y0 + h))
        return cropped.convert("RGBA")

    # Fallback procedural wash if PNG is missing
    import numpy as np

    yy = np.linspace(0.0, 1.0, h, dtype=np.float64)[:, None]
    t = yy
    c0 = np.array(GRAD_TOP, dtype=np.float64)
    c1 = np.array(GRAD_MID, dtype=np.float64)
    c2 = np.array(GRAD_BOT, dtype=np.float64)
    t1 = np.clip(t / 0.45, 0.0, 1.0)
    t2 = np.clip((t - 0.45) / 0.55, 0.0, 1.0)
    t1s = t1 * t1 * (3.0 - 2.0 * t1)
    t2s = t2 * t2 * (3.0 - 2.0 * t2)
    top_mid = c0[None, None, :] * (1 - t1s[..., None]) + c1[None, None, :] * t1s[..., None]
    mid_bot = c1[None, None, :] * (1 - t2s[..., None]) + c2[None, None, :] * t2s[..., None]
    rgb = np.where((t > 0.45)[..., None], mid_bot, top_mid)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")


def soft_shadow(base, box, radius, alpha=48, blur=14, dy=8):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (x0, y0 + dy, x1, y1 + dy), radius=radius, fill=(*SHADOW, alpha)
    )
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def css_like_window_shadow(base, box, radius=22):
    """Match CS1 hero-window shadow: soft, wide, low-opacity (CSS-quality for PNG poster).

    CS1: box-shadow: 0 1.76cqw 3.91cqw rgba(60, 40, 90, 0.22)
    """
    x0, y0, x1, y1 = box
    w = max(1, x1 - x0)
    # Approximate cqw from window width (CS1 window is ~30% of stage; blur scales with stage)
    # Use window width as reference so shadow reads similarly at card + hero sizes.
    dy = max(8, int(round(w * 0.058)))   # ~1.76% of stage ≈ 5.8% of window
    blur = max(16, int(round(w * 0.13)))  # ~3.91% of stage ≈ 13% of window
    soft_shadow(base, box, radius=radius, alpha=int(255 * 0.22), blur=blur, dy=dy)


def make_trigger_card(size: int = 192) -> Image.Image:
    """Hi-res recreation of the screenshot tag trigger card."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 48)
    radius = max(14, size // 6)
    d.rounded_rectangle((pad, pad, size - pad - 1, size - pad - 1), radius=radius, fill=WHITE)
    d.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=radius,
        outline=(228, 230, 235),
        width=max(1, size // 96),
    )
    cx = cy = size // 2
    r = int(size * 0.30)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(238, 241, 255))
    # Diagonal tag (purple), crisp strokes
    fg = (88, 70, 200)
    s = size / 192
    w = max(3, int(3.5 * s))
    # tag body as rounded diamond-ish path
    pts = [
        (cx - 4 * s, cy - 28 * s),
        (cx + 28 * s, cy - 4 * s),
        (cx + 4 * s, cy + 28 * s),
        (cx - 28 * s, cy + 4 * s),
    ]
    d.line(pts + [pts[0]], fill=fg, width=w, joint="curve")
    # hole
    hr = 5 * s
    d.ellipse((cx - 14 * s - hr, cy - 14 * s - hr, cx - 14 * s + hr, cy - 14 * s + hr), outline=fg, width=w)
    return img


def make_plus_btn(size: int = 72) -> Image.Image:
    """White circle with a perfectly centered +."""
    # Use odd size so a true center pixel exists
    size = size if size % 2 == 1 else size + 1
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Circle inset 1px so stroke stays inside bounds
    d.ellipse((1, 1, size - 2, size - 2), fill=WHITE, outline=(210, 214, 220), width=max(1, size // 28))
    cx = cy = size // 2
    arm = max(4, int(size * 0.22))
    thick = max(2, size // 12)
    # Draw as centered rectangles (avoids line-cap bias)
    half_t = thick // 2
    # Horizontal bar
    d.rectangle((cx - arm, cy - half_t, cx + arm, cy + half_t), fill=(110, 116, 126))
    # Vertical bar
    d.rectangle((cx - half_t, cy - arm, cx + half_t, cy + arm), fill=(110, 116, 126))
    return img


def make_end_pill(height: int = 44, width: int | None = None, scale: float = 1.0) -> Image.Image:
    """Capsule “End” pill — width matches action cards when provided."""
    height = max(24, int(height))
    # Larger type, regular weight (not bold)
    font_size = max(14, int(height * 0.58))
    font = load_font(font_size, bold=False)
    text = "End"
    if width is None:
        probe = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        pad_x = max(7, int(font_size * 0.42))
        width = max(int(tw + pad_x * 2), height + int(font_size * 0.15))
    else:
        width = max(int(width), height)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stroke = max(1, height // 22)
    # Soft light-blue pill (lighter than the previous fill)
    d.rounded_rectangle(
        (stroke, stroke, width - stroke - 1, height - stroke - 1),
        radius=height / 2,
        fill=(236, 245, 255),
        outline=(196, 220, 248),
        width=stroke,
    )
    d.text((width / 2, height / 2), text, font=font, fill=(40, 70, 120), anchor="mm")
    return img


def load_parts(scale: float = 1.0):
    """Procedural hi-res parts (not upscaled crops)."""
    card_size = max(160, int(192 * scale))
    trig = make_trigger_card(size=card_size)
    plus = make_plus_btn(size=max(56, int(72 * scale)))
    # Same width as boxes; height keeps the short pill proportion (32/128 of card)
    end = make_end_pill(height=max(40, int(card_size * 0.25)), width=card_size, scale=scale)
    return trig, plus, end


def make_action_card(kind: str, size: int = 192) -> Image.Image:
    """Match the screenshot's white rounded card + tinted icon circle."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 64)
    radius = max(16, size // 6)
    d.rounded_rectangle((pad, pad, size - pad - 1, size - pad - 1), radius=radius, fill=WHITE)
    d.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=radius,
        outline=(230, 232, 236),
        width=max(1, size // 96),
    )
    cx = cy = size // 2
    r = int(size * 0.30)
    if kind == "mail":
        bg, fg = (220, 236, 255), (55, 110, 200)
    elif kind == "sms":
        bg, fg = (214, 244, 230), (40, 140, 100)
    else:
        bg, fg = (255, 236, 220), (200, 110, 50)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg)
    s = size / 192
    stroke = max(2, int(3.2 * s))
    if kind == "mail":
        d.rounded_rectangle(
            (cx - 28 * s, cy - 20 * s, cx + 28 * s, cy + 20 * s),
            radius=max(3, int(4 * s)),
            outline=fg,
            width=stroke,
        )
        d.line(
            (cx - 24 * s, cy - 10 * s, cx, cy + 6 * s, cx + 24 * s, cy - 10 * s),
            fill=fg,
            width=stroke,
        )
    elif kind == "sms":
        d.rounded_rectangle(
            (cx - 26 * s, cy - 20 * s, cx + 26 * s, cy + 12 * s),
            radius=max(8, int(12 * s)),
            fill=fg,
        )
        d.polygon(
            [(cx - 4 * s, cy + 12 * s), (cx - 16 * s, cy + 28 * s), (cx + 8 * s, cy + 12 * s)],
            fill=fg,
        )
        for dx in (-10, 0, 10):
            d.ellipse(
                (cx + dx * s - 4 * s, cy - 4 * s, cx + dx * s + 4 * s, cy + 4 * s),
                fill=bg,
            )
    else:
        pts = [
            (cx - 6 * s, cy - 28 * s),
            (cx + 28 * s, cy - 6 * s),
            (cx + 6 * s, cy + 28 * s),
            (cx - 28 * s, cy + 6 * s),
        ]
        d.line(pts + [pts[0]], fill=fg, width=stroke, joint="curve")
        d.ellipse((cx - 16 * s - 5 * s, cy - 16 * s - 5 * s, cx - 16 * s + 5 * s, cy - 16 * s + 5 * s), outline=fg, width=stroke)
    return img


def paste_scaled(dst, src, cx, cy, scale, opacity, rotate=0.0):
    if opacity <= 0.01 or scale <= 0.01:
        return
    w, h = src.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    piece = src.resize((nw, nh), Image.Resampling.LANCZOS)
    if abs(rotate) > 0.05:
        piece = piece.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=True)
    if opacity < 0.999:
        a = piece.split()[-1].point(lambda p: int(p * opacity))
        piece.putalpha(a)
    pw, ph = piece.size
    dst.alpha_composite(piece, (int(cx - pw / 2), int(cy - ph / 2)))


def hero_float(t: float, delay: float, amp: float, period: float = 6.0):
    """Match CS1 `.hero-float`: ease-in-out Y bob + slight tilt, staggered delay.

    CSS: 0/100% → translateY(0) rotate(-0.5deg); 50% → translateY(-5px) rotate(0.5deg)
    """
    phase = ((t + delay) % period) / period
    # Smooth 0→1→0 (approx ease-in-out between keyframes)
    w = 0.5 - 0.5 * math.cos(phase * 2.0 * math.pi)
    dy = -amp * w
    rot = -0.5 + w  # -0.5deg → +0.5deg
    return dy, rot


def draw_dots(draw, x0, y0, x1, y1, step=18, radius=1):
    for y in range(y0 + step // 2, y1, step):
        for x in range(x0 + step // 2, x1, step):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=DOT)


def draw_dashed(draw, x, y0, y1, progress_t, phase=0.0, opacity=1.0, width=3):
    """Draw a dashed vertical connector. Pattern is locked to y0 so segments
    stay visually stable once drawn (no marching gaps at the endpoints)."""
    if progress_t <= 0.01 or y1 <= y0 + 0.5:
        return
    # Snap to full once mostly drawn so the line never "breathes"
    amt = 1.0 if progress_t >= 0.98 else max(0.0, min(1.0, progress_t))
    y_end = y0 + (y1 - y0) * amt
    dash, gap = 10, 8
    # Fixed alignment from y0 — phase only shifts pattern while drawing in
    offset = 0.0 if amt >= 1.0 else (phase % (dash + gap))
    y = y0 - offset
    col = (*DASH, int(220 * opacity))
    while y < y_end:
        ys = max(y, y0)
        ye = min(y + dash, y_end)
        if ye > ys:
            draw.line((x, ys, x, ye), fill=col, width=width)
        y += dash + gap


def draw_ripple(draw, cx, cy, t, color=(96, 196, 168), width=2):
    if t <= 0 or t > 1:
        return
    r = 12 + t * 48
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*color, int(160 * (1 - t))), width=width)


def draw_spark(draw, cx, cy, s, fill, a=255):
    pts = [
        (cx, cy - s),
        (cx + s * 0.22, cy - s * 0.22),
        (cx + s, cy),
        (cx + s * 0.22, cy + s * 0.22),
        (cx, cy + s),
        (cx - s * 0.22, cy + s * 0.22),
        (cx - s, cy),
        (cx - s * 0.22, cy - s * 0.22),
    ]
    draw.polygon(pts, fill=(*fill, a))


def layout_metrics(out_w: int, out_h: int):
    """Shared layout numbers used by render_scene + camera framing."""
    s = out_w / 1440
    px0, py0, px1, py1 = window_box(out_w, out_h)
    hdr_h = int(52 * s)
    cx = (px0 + px1) / 2
    canvas_top = py0 + hdr_h
    canvas_bot = py1
    actions = [("mail", 2.15), ("offer", 3.55)]
    n_cards = 1 + len(actions)
    card = int(136 * s)
    gap = int(52 * s)
    end_h = int(34 * s)
    gap_end = int(gap * 1.28)
    bottom_pad = int(36 * s)
    top_pad = int(28 * s)
    plus_r = int(22 * s)

    stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
    available = canvas_bot - canvas_top - top_pad - bottom_pad
    if stack_h > available:
        overflow = stack_h - available
        gap = max(int(40 * s), gap - int(overflow / max(1, n_cards)))
        gap_end = int(gap * 1.28)
        stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
        if stack_h > available:
            card = max(int(100 * s), card - int((stack_h - available) / n_cards))
            stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
    top = canvas_top + top_pad + max(0, (available - stack_h) // 2)

    def slot_y(i: int) -> float:
        return top + card / 2 + i * (card + gap)

    centers = [slot_y(i) for i in range(n_cards)]
    starts = [0.45] + [st for _, st in actions]
    end_appear_t = starts[-1] + 0.70

    def end_y_for(card_index: int) -> float:
        return centers[card_index] + card / 2 + gap_end + end_h / 2

    end_y = min(end_y_for(n_cards - 1), canvas_bot - bottom_pad - end_h / 2)
    return {
        "s": s,
        "cx": cx,
        "px0": px0,
        "py0": py0,
        "px1": px1,
        "py1": py1,
        "hdr_h": hdr_h,
        "card": card,
        "gap": gap,
        "gap_end": gap_end,
        "end_h": end_h,
        "plus_r": plus_r,
        "centers": centers,
        "starts": starts,
        "actions": actions,
        "end_y": end_y,
        "end_appear_t": end_appear_t,
    }


def camera_focus_y(t: float, m: dict, view_h: float) -> float:
    """Pan focus down as each new node appears — one box + plus/lines in frame.

    Opens on the window’s grey header bar, and settles so the full End pill is visible.
    """
    centers = m["centers"]
    gap = m["gap"]
    end_y = m["end_y"]
    end_h = m["end_h"]
    starts = m["starts"]
    end_appear_t = m["end_appear_t"]
    py0 = m["py0"]
    out_bot = float(m["py1"] + 8)

    # Bias slightly below card center so line-above + box + plus-below all read
    def box_focus(i: int) -> float:
        return centers[i] + gap * 0.22

    # Crop top pinned near window top → grey header fully in frame
    header_focus = py0 + view_h * 0.5 - 2.0
    # Crop bottom pinned below End pill → full capsule visible
    end_bottom = end_y + end_h * 0.5 + 18.0
    end_focus = end_bottom - view_h * 0.5
    # Keep end focus from pushing past the renderable area
    max_focus = out_bot - view_h * 0.5
    end_focus = min(end_focus, max_focus)

    waypoints = [
        (0.0, header_focus),
        (starts[0] + 0.55, header_focus),  # hold: grey bar + first card
        (starts[0] + 1.05, box_focus(0)),
        (starts[1] - 0.05, box_focus(0)),
        (starts[1] + 0.55, box_focus(1)),
        (starts[2] - 0.05, box_focus(1)),
        (starts[2] + 0.55, box_focus(2)),
        (end_appear_t - 0.05, box_focus(2)),
        (end_appear_t + 0.45, end_focus),
        (end_appear_t + 3.0, end_focus),
    ]

    if t <= waypoints[0][0]:
        return waypoints[0][1]
    for i in range(len(waypoints) - 1):
        t0, y0 = waypoints[i]
        t1, y1 = waypoints[i + 1]
        if t <= t1:
            u = ease_in_out(clamp01((t - t0) / max(0.001, t1 - t0)))
            return lerp(y0, y1, u)
    return waypoints[-1][1]


def make_dot_canvas(w: int, h: int, step: int = 20, radius: int = 1) -> Image.Image:
    """Full-bleed Automations canvas (grey + dots) for hero edge-to-edge fill."""
    img = Image.new("RGBA", (w, h), (*CANVAS, 255))
    d = ImageDraw.Draw(img)
    # Slightly stronger than in-window dots so the grid reads after GIF quantize
    dot = (198, 201, 206)
    r = max(2, radius)
    for y in range(r + 2, h, max(14, step)):
        for x in range(r + 2, w, max(14, step)):
            d.ellipse((x - r, y - r, x + r, y + r), fill=(*dot, 255))
    return img


def apply_hero_camera(frame: Image.Image, t: float, out_w: int, out_h: int) -> Image.Image:
    """Crop a zoomed viewport (1 box + connectors/plus) and fit CS1/CS2 hero aspect.

    Side gutters are filled with the dotted canvas so grey extends to the frame edges
    (instead of showing the page gradient through transparency).
    """
    m = layout_metrics(out_w, out_h)
    card = m["card"]
    gap = m["gap"]
    plus_r = m["plus_r"]
    cx = m["cx"]
    px0, px1 = m["px0"], m["px1"]
    end_y = m["end_y"]
    end_h = m["end_h"]
    py0 = m["py0"]
    hdr_h = m["hdr_h"]
    s = m["s"]

    # Tall enough for dashed line above, one card, plus, and line below —
    # and tall enough that header→first card / last card→End can both fit.
    view_h = float(card + gap + plus_r * 2.4)
    view_h = max(view_h, float(hdr_h + card + gap * 0.85))
    view_h = max(view_h, float(card * 0.55 + m["gap_end"] + end_h + 28))
    view_w = view_h * HERO_ASPECT
    win_w = float(px1 - px0)
    if view_w < win_w * 1.06:
        view_w = win_w * 1.06
        view_h = view_w / HERO_ASPECT

    view_h = min(view_h, float(out_h) * 0.98)
    view_w = view_h * HERO_ASPECT
    if view_w > out_w:
        view_w = float(out_w)
        view_h = view_w / HERO_ASPECT

    fy = camera_focus_y(t, m, view_h)
    x0 = max(0.0, min(float(out_w) - view_w, cx - view_w / 2))
    y0 = max(0.0, min(float(out_h) - view_h, fy - view_h / 2))

    # Hard guarantees: opening shows grey header; finale shows full End pill
    if t < m["starts"][0] + 0.7:
        y0 = min(y0, max(0.0, py0 - 6.0))
    if t >= m["end_appear_t"] + 0.35:
        end_bottom = end_y + end_h * 0.5 + 16.0
        y0 = min(y0, max(0.0, float(out_h) - view_h))
        y0 = max(y0, min(float(out_h) - view_h, end_bottom - view_h))

    x1 = x0 + view_w
    y1 = y0 + view_h

    cw = max(1, int(round(x1)) - int(round(x0)))
    ch = max(1, int(round(y1)) - int(round(y0)))
    cropped = frame.crop((int(round(x0)), int(round(y0)), int(round(x0)) + cw, int(round(y0)) + ch))

    # Scale UI first, then paint dots at final resolution so the grid stays crisp
    # edge-to-edge (small pre-resize dots were washing out in the side gutters).
    ui = cropped.resize((HERO_W, HERO_H), Image.Resampling.LANCZOS)
    step = max(22, int(round(28 * (HERO_W / 1440))))
    base = make_dot_canvas(HERO_W, HERO_H, step=step, radius=max(2, int(round(2.2 * (HERO_W / 1440)))))
    # Extend the top chrome bar edge-to-edge when it’s in frame (map hdr into resized space)
    scale_y = HERO_H / max(1, ch)
    hdr_top = (py0 - y0) * scale_y
    hdr_bot = (py0 + hdr_h - y0) * scale_y
    if hdr_bot > 0 and hdr_top < HERO_H:
        yd = ImageDraw.Draw(base)
        y_a = max(0, int(round(hdr_top)))
        y_b = min(HERO_H, int(round(hdr_bot)))
        if y_b > y_a:
            yd.rectangle((0, y_a, HERO_W, y_b), fill=(*WHITE, 255))
            if 0 <= y_b < HERO_H:
                yd.line((0, y_b, HERO_W, y_b), fill=(228, 230, 234, 255), width=max(1, int(round(s * HERO_W / max(1, cw)))))
    base.alpha_composite(ui)
    return base


def window_box(out_w, out_h):
    """Same floating-window geometry as render_scene."""
    s = out_w / 1440
    card_ref = int(128 * s)
    win_w = int(card_ref * 3.05)
    win_h = int(out_h * 0.86)
    win_w = min(win_w, int(out_w * 0.48))
    win_h = min(win_h, int(out_h * 0.90))
    px0 = (out_w - win_w) // 2
    py0 = (out_h - win_h) // 2
    return px0, py0, px0 + win_w, py0 + win_h


def render_scene(t, out_w, out_h, grad, parts):
    """Compose UI layers on a transparent field (gradient comes from CSS/PNG).

    Layers:
      1. (gradient is external — not baked into the GIF)
      2. Floating window (canvas, dot grid, header, title) — no baked shadow
      3. Dashed connectors
      4. Plus buttons (pulse/spin)
      5. Node cards (trigger → mail → offer)
      6. End pill (always below the lowest card — never overlapping)
      7. Sparks / ripples on top
    """
    trigger, plus, end = parts
    # Transparent — site shows the uploaded PNG behind this GIF
    bg = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    s = out_w / 1440

    px0, py0, px1, py1 = window_box(out_w, out_h)
    hdr_h = int(52 * s)

    # --- Layer 2: floating window ---
    # Shadow is NOT baked into the GIF (GIF banding). Live pages use CSS
    # filter: drop-shadow matching CS1. Poster still gets a smooth PNG shadow.
    win_p = 1.0
    if win_p > 0.01:
        panel = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        a = int(255 * win_p)
        # Full window = light grey canvas
        pd.rounded_rectangle((px0, py0, px1 - 1, py1 - 1), radius=18, fill=(*CANVAS, a))
        # White header only above the divider
        pd.rounded_rectangle((px0, py0, px1 - 1, py0 + hdr_h + 18), radius=18, fill=(*WHITE, a))
        pd.rectangle((px0, py0 + hdr_h, px1 - 1, py0 + hdr_h + 20), fill=(*CANVAS, a))
        pd.line((px0 + 1, py0 + hdr_h, px1 - 2, py0 + hdr_h), fill=(228, 230, 234, a), width=max(1, int(s)))
        draw_dots(
            pd,
            px0 + 8,
            py0 + hdr_h + 1,
            px1 - 8,
            py1 - 10,
            step=max(18, int(20 * s)),
            radius=max(1, int(1.6 * s)),
        )
        bg.alpha_composite(panel)
        font = load_font(max(16, int(22 * s)), bold=True)
        d = ImageDraw.Draw(bg)
        title = "New automation"
        # True vertical + horizontal center in the header bar
        d.text(
            ((px0 + px1) / 2, py0 + hdr_h / 2),
            title,
            font=font,
            fill=(*TEXT, int(255 * win_p)),
            anchor="mm",
        )

    # --- Layout: even optical rhythm inside the canvas ---
    # Pattern:  card · (gap/2 · plus · gap/2) · card · … · (gap/2 · plus · gap/2) · End
    cx = (px0 + px1) / 2
    canvas_top = py0 + hdr_h
    canvas_bot = py1
    actions = [("mail", 2.15), ("offer", 3.55)]
    n_cards = 1 + len(actions)

    # Slightly larger nodes now that the panel is narrower
    card = int(136 * s)
    gap = int(52 * s)
    end_h = int(34 * s)
    # Match action-card width exactly
    end_w = card
    # Slightly longer final gap so the last dashed line (plus → End) reads longer
    gap_end = int(gap * 1.28)
    bottom_pad = int(36 * s)
    top_pad = int(28 * s)
    plus_r = int(22 * s)

    stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
    available = canvas_bot - canvas_top - top_pad - bottom_pad
    if stack_h > available:
        # Prefer slightly smaller gaps before shrinking cards
        overflow = stack_h - available
        gap = max(int(40 * s), gap - int(overflow / max(1, n_cards)))
        gap_end = int(gap * 1.28)
        stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
        if stack_h > available:
            card = max(int(100 * s), card - int((stack_h - available) / n_cards))
            end_w = card
            stack_h = n_cards * card + (n_cards - 1) * gap + gap_end + end_h
    top = canvas_top + top_pad + max(0, (available - stack_h) // 2)

    def slot_y(i: int) -> float:
        return top + card / 2 + i * (card + gap)

    y_trigger = slot_y(0)
    centers = [slot_y(i) for i in range(n_cards)]
    starts = [0.45] + [st for _, st in actions]

    def end_y_for(card_index: int) -> float:
        return centers[card_index] + card / 2 + gap_end + end_h / 2

    # End only appears after the last plus reaction — final slot under the last card
    end_y_final = min(end_y_for(n_cards - 1), canvas_bot - bottom_pad - end_h / 2)
    end_y = end_y_final
    end_appear_t = starts[-1] + 0.70  # after last-plus click (~starts[-1]+0.55)
    end_reveal = progress(t, end_appear_t, 0.4, ease_out_back)

    # Content drawn into a separate layer, then clipped to the window
    content = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    lines = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    nodes = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    fx = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    fd = ImageDraw.Draw(fx)
    phase = t * 18
    dash_w = max(2, int(3 * s))
    trig_base = card / max(trigger.size[0], 1)

    # --- Layer 3: connectors (behind cards) ---
    # Each segment draws once, then stays at full length for the rest of the loop.
    for i in range(n_cards):
        if progress(t, starts[i], 0.40) <= 0.35:
            continue
        y_from = centers[i] + card * 0.48
        if i < len(actions):
            next_st = actions[i][1]
            plus_st = next_st - 0.55
            y_plus = (centers[i] + centers[i + 1]) / 2
            draw_dashed(
                ld,
                cx,
                y_from,
                y_plus - plus_r * 0.95,
                progress(t, plus_st, 0.4),
                phase,
                width=dash_w,
            )
            draw_dashed(
                ld,
                cx,
                y_plus + plus_r * 0.95,
                centers[i + 1] - card * 0.48,
                progress(t, next_st - 0.1, 0.35),
                phase + 5,
                width=dash_w,
            )
        else:
            # Last card → plus (early); plus → End only once End appears
            y_plus = centers[i] + card * 0.5 + gap_end / 2
            # Reach a bit closer to End so the last segment reads longer
            end_top = end_y_final - end_h * 0.38
            draw_dashed(
                ld,
                cx,
                y_from,
                y_plus - plus_r * 0.95,
                progress(t, starts[i] + 0.2, 0.35),
                0.0,
                width=dash_w,
            )
            draw_dashed(
                ld,
                cx,
                y_plus + plus_r * 0.85,
                end_top,
                progress(t, end_appear_t, 0.35),
                0.0,
                width=dash_w,
            )

    content.alpha_composite(lines)

    # --- Layer 4: plus buttons (between cards + between last card and End) ---
    def draw_plus_at(y_plus: float, appear_t: float, click_t: float | None = None):
        pp = progress(t, appear_t, 0.35, ease_out_back)
        if pp <= 0.01:
            return
        pulse, rot = 1.0, 0.0
        if click_t is not None and t >= click_t:
            pulse = 1.0 + 0.18 * math.sin(clamp01((t - click_t) / 0.4) * math.pi)
            # Keep rotation a multiple of 90 so the + stays axis-aligned / centered
            rot = 90.0 * ease_out_cubic(clamp01((t - click_t) / 0.4))
        # Scale so the drawn circle diameter == 2 * plus_r (true center at cx, y_plus)
        target = plus_r * 2
        paste_scaled(
            content,
            plus,
            cx,
            y_plus,
            (target / plus.size[0]) * pulse * (0.55 + 0.45 * min(pp, 1)),
            clamp01(pp * 1.2),
            rot,
        )
        if click_t is not None and t >= click_t:
            draw_ripple(fd, cx, y_plus, clamp01((t - click_t) / 0.55), width=max(2, int(2.5 * s)))

    for i in range(len(actions)):
        next_st = actions[i][1]
        draw_plus_at(
            (centers[i] + centers[i + 1]) / 2,
            next_st - 0.55 + 0.08,
            click_t=next_st - 0.15,
        )

    # Plus between last square and End — same green ripple reaction as the others
    if progress(t, starts[-1], 0.4) > 0.35:
        y_plus_end = centers[-1] + card * 0.5 + gap_end / 2
        draw_plus_at(y_plus_end, starts[-1] + 0.25, click_t=starts[-1] + 0.55)

    # --- Layer 5: node cards (CS1-style float once settled) ---
    # Staggered delays like CS1 chips (animation-delay: -.2s, -1.3s, …)
    float_amp = 5.0 * s  # CS1 uses -5px peak
    float_delays = (0.2, 1.3, 2.1)

    trig_p = progress(t, starts[0], 0.5, ease_out_back)
    if trig_p > 0.01:
        rot = (1 - min(trig_p, 1)) * -10
        sc = trig_base * (0.55 + 0.45 * min(trig_p, 1.06))
        if trig_p > 1:
            sc = trig_base * (1.06 - 0.06 * clamp01((trig_p - 1) / 0.45))
        fy, frot = (0.0, 0.0)
        if trig_p >= 0.98:
            fy, frot = hero_float(t, float_delays[0], float_amp)
        paste_scaled(
            nodes,
            trigger,
            cx,
            y_trigger + fy,
            sc,
            clamp01(trig_p * 1.2),
            rot + frot,
        )
        if 0.75 < trig_p < 1.15:
            draw_spark(
                fd,
                cx + card * 0.46,
                y_trigger - card * 0.38,
                9 * s,
                SPARK,
                int(200 * (1 - abs(trig_p - 1))),
            )

    imgs = {
        "mail": make_action_card("mail", size=max(160, int(220 * s))),
        "offer": make_action_card("offer", size=max(160, int(220 * s))),
    }
    for i, (kind, st) in enumerate(actions):
        p = progress(t, st, 0.5, ease_out_back)
        if p <= 0.01:
            continue
        cy = centers[i + 1]
        y_plus = (centers[i] + cy) / 2
        cy_anim = lerp(y_plus, cy, clamp01(p * 1.2))
        sc = 0.55 + 0.45 * min(p, 1.05)
        if p > 1:
            sc = 1.05 - 0.05 * clamp01((p - 1) / 0.45)
        rot = (1 - min(p, 1)) * (8 if i % 2 == 0 else -8)
        fy, frot = (0.0, 0.0)
        if p >= 0.98:
            fy, frot = hero_float(t, float_delays[i + 1], float_amp)
        paste_scaled(
            nodes,
            imgs[kind],
            cx,
            cy_anim + fy,
            sc * (card / imgs[kind].size[0]),
            clamp01(p * 1.15),
            rot + frot,
        )
        if 0.75 < p < 1.15:
            draw_spark(
                fd,
                cx + card * 0.44,
                cy - card * 0.36,
                8 * s,
                SPARK,
                int(180 * (1 - abs(p - 1))),
            )

    content.alpha_composite(nodes)

    # --- Layer 6: End pill (same width as action boxes) ---
    if end_reveal > 0.01:
        pop = 0.82 + 0.18 * min(end_reveal, 1)
        fy, frot = (0.0, 0.0)
        if end_reveal >= 0.98:
            fy, frot = hero_float(t, 0.8, float_amp * 0.7, period=5.8)
        # Scale so rendered width == end_w (== card)
        paste_scaled(
            content,
            end,
            cx,
            end_y + fy,
            pop * (end_w / end.size[0]),
            clamp01(end_reveal * 1.2),
            frot,
        )

    # --- Layer 7: finale sparks (with End reveal) ---
    if end_appear_t + 0.15 < t < end_appear_t + 1.15:
        finale = clamp01((t - (end_appear_t + 0.15)) / 0.5)
        fade = 1.0 if t < end_appear_t + 0.75 else clamp01((end_appear_t + 1.15 - t) / 0.4)
        for j, (ang, dist) in enumerate(((30, 0.5), (150, 0.48), (85, 0.58), (280, 0.42), (220, 0.55))):
            rad = math.radians(ang + t * 18)
            sx = cx + math.cos(rad) * card * dist * min(finale, 1)
            sy = end_y - card * 0.08 + math.sin(rad) * card * 0.18 * min(finale, 1)
            draw_spark(
                fd,
                sx,
                sy,
                (6 + j) * s * (0.55 + 0.45 * finale),
                (255, 215, 90),
                int(190 * fade * (1 - finale * 0.15)),
            )
    content.alpha_composite(fx)

    # Clip all content to the floating window so nothing bleeds onto the gradient
    if win_p > 0.01:
        mask = Image.new("L", bg.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (px0 + 2, py0 + hdr_h + 1, px1 - 3, py1 - 3),
            radius=14,
            fill=int(255 * win_p),
        )
        # Keep header title area clear of nodes (already drawn on bg)
        clipped = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        clipped.paste(content, (0, 0), mask)
        bg.alpha_composite(clipped)

    return bg  # keep RGBA for transparent GIF export


def quantize_rgba_frames(rgba_frames, grad, colors=200):
    """GIF with transparency outside the UI; soft shadow kept (no black fringe).

    Semi-transparent pixels (shadow / AA) are pre-composited onto the same
    gradient used in CSS, then treated as opaque. Only fully empty pixels stay
    transparent — so RGB conversion never falls back to black.
    """
    import numpy as np

    grad_rgba = grad.convert("RGBA")
    # Flatten UI onto gradient first (shadow becomes darkened gradient, not black)
    flat_frames = []
    empty_masks = []
    for fr in rgba_frames:
        rgba = fr.convert("RGBA")
        alpha = np.array(rgba.getchannel("A"))
        flat = Image.alpha_composite(grad_rgba, rgba)
        flat_frames.append(flat.convert("RGB"))
        # Keep anything with visible coverage (incl. soft shadow) opaque in GIF
        empty_masks.append(alpha < 8)

    # Shared palette from composited frames (includes shadow teal mix)
    idxs = sorted({0, len(flat_frames) // 4, len(flat_frames) // 2, (3 * len(flat_frames)) // 4, len(flat_frames) - 1})
    samples = []
    for idx in idxs:
        arr = np.array(flat_frames[idx])
        keep = ~empty_masks[idx]
        if keep.any():
            samples.append(arr[keep])
    if samples:
        pix = np.concatenate(samples, axis=0)
        if len(pix) > 80000:
            pix = pix[:: len(pix) // 80000]
        sheet = Image.fromarray(pix.reshape(-1, 1, 3).repeat(4, axis=1), "RGB")
    else:
        sheet = Image.new("RGB", (64, 64), (255, 255, 255))

    seeds = [
        (255, 255, 255), (244, 245, 247), (228, 230, 234),
        (238, 241, 255), (88, 70, 200), (220, 236, 255), (55, 110, 200),
        (214, 244, 230), (40, 140, 100), (255, 236, 220), (200, 110, 50),
        (236, 245, 255), (196, 220, 248), (40, 70, 120), (120, 126, 136),
        # Shadow / gradient mix tones (prevent black fringe)
        (90, 204, 228), (116, 215, 211), (149, 227, 187),
        (70, 160, 170), (55, 130, 140), (45, 110, 120), (35, 90, 100),
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
    for rgb, empty in zip(flat_frames, empty_masks):
        q = rgb.quantize(palette=master, dither=Image.Dither.NONE)
        pal = (q.getpalette() or []) + [0] * 768
        pal = pal[:768]
        # Transparent key — match a mid gradient so any bleed is invisible
        pal[765:768] = [116, 215, 211]
        pix = np.array(q, dtype=np.uint8)
        pix[empty] = 255
        out = Image.fromarray(pix, mode="P")
        out.putpalette(pal)
        out.info["transparency"] = 255
        frames.append(out)
    return frames


def build():
    parts_card = load_parts(scale=2.2)
    parts_hero = load_parts(scale=2.6)
    # Slower playback (~2×): same animation t-keys, longer frame holds
    build_times = [i * 0.22 for i in range(0, 28)]  # 0 .. 5.94
    idle_times = [6.2 + i * 0.38 for i in range(16)]  # floating hold
    key_times = build_times + idle_times
    # Card keeps original pace; hero header plays slower
    card_durations = [160] * len(build_times) + [300] * len(idle_times)
    hero_durations = [320] * len(build_times) + [500] * len(idle_times)

    # Source canvas for hero camera (full overview), then crop/zoom to HERO_W×HERO_H
    SRC_W, SRC_H = CARD_W, CARD_H
    hero_grad_src = make_gradient(SRC_W, SRC_H)
    hero_grad = make_gradient(HERO_W, HERO_H)
    card_grad = make_gradient(CARD_W, CARD_H)

    card_rgba = [render_scene(t, CARD_W, CARD_H, card_grad, parts_card) for t in key_times]
    hero_src = [render_scene(t, SRC_W, SRC_H, hero_grad_src, parts_hero) for t in key_times]
    hero_rgba = [apply_hero_camera(fr, t, SRC_W, SRC_H) for fr, t in zip(hero_src, key_times)]

    card_frames = quantize_rgba_frames(card_rgba, card_grad)
    hero_frames = quantize_rgba_frames(hero_rgba, hero_grad)

    card_frames[0].save(
        OUT_CARD,
        save_all=True,
        append_images=card_frames[1:],
        duration=card_durations,
        loop=0,
        optimize=False,
        disposal=2,
        transparency=255,
    )

    # Poster: zoomed hero frame with CS1-smooth shadow
    poster = hero_grad.convert("RGBA")
    # Approximate shadow under the visible window chrome in the cropped frame
    css_like_window_shadow(
        poster,
        (int(HERO_W * 0.18), int(HERO_H * 0.06), int(HERO_W * 0.82), int(HERO_H * 0.94)),
        radius=18,
    )
    poster.alpha_composite(hero_rgba[min(len(hero_rgba) - 1, len(build_times) // 2)])
    poster.convert("RGB").save(OUT_POSTER, "PNG", optimize=True)

    hero_frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=hero_frames[1:],
        duration=hero_durations,
        loop=0,
        optimize=False,
        disposal=2,
        transparency=255,
    )

    print(f"Wrote {OUT_CARD.name} ({OUT_CARD.stat().st_size / 1024:.0f} KB) {CARD_W}x{CARD_H}, {len(card_frames)} frames, {sum(card_durations)/1000:.1f}s")
    print(f"Wrote {OUT_GIF.name} ({OUT_GIF.stat().st_size / 1024:.0f} KB) {HERO_W}x{HERO_H} (camera zoom), {len(hero_frames)} frames, {sum(hero_durations)/1000:.1f}s")


if __name__ == "__main__":
    build()
