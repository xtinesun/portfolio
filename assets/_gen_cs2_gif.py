"""CS2 project-card GIF — clear hierarchy, readable at list-card size."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "cs2-project-card.gif"
PREVIEW = Path(__file__).resolve().parent / "_preview-cs2-s0.png"

W, H = 1080, 675
FPS = 12

# Hierarchy colors
INK = (18, 16, 22)          # primary
INK_2 = (55, 52, 48)        # secondary
INK_3 = (120, 114, 106)     # tertiary / labels
MUTED_BG = (242, 240, 236)
LINE = (232, 228, 222)


def font(name, size):
    for p in (
        f"/System/Library/Fonts/Supplemental/{name}.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# Type scale — weight + size create hierarchy (not size alone)
f_h = font("Arial Bold", 34)          # 1. Product title
f_step = font("Arial Bold", 15)       # 2. Progress chrome (quiet)
f_scene = font("Arial", 22)           # 3. Scene beat (supporting, not bold)
f_variant = font("Arial", 18)         # card meta
f_subj = font("Arial Bold", 21)       # card primary content
f_metric = font("Arial Bold", 36)     # data hero
f_metric_lbl = font("Arial Bold", 12) # data label
f_letter = font("Arial Bold", 24)
f_status = font("Arial Bold", 15)     # tertiary state

# Variant card spacing — one rhythm for A and B (keeps frames stable)
VC_PAD_TOP = 28          # below accent → badge (more air under top)
VC_BADGE_R = 22
VC_GAP_BADGE_SUBJ = 22   # badge → subject (more air under A/B)
VC_SUBJ_LINE = 26        # subject line box
VC_SUBJ_LINES = 2        # both subjects are two lines
VC_GAP_TO_METRICS = 18   # subject → OPEN RATE (section break)
VC_GAP_LABEL_PCT = 6     # OPEN RATE → % (tight pair)
VC_PCT_H = 36            # % ink height budget
VC_PAD_BOTTOM = 18       # below last content

# Card height fits the full stack (badge → 2-line subject → metrics) + equal pads
VC_H = (
    VC_PAD_TOP
    + VC_BADGE_R * 2
    + VC_GAP_BADGE_SUBJ
    + VC_SUBJ_LINE * VC_SUBJ_LINES
    + VC_GAP_TO_METRICS
    + 14  # label
    + VC_GAP_LABEL_PCT
    + VC_PCT_H
    + VC_PAD_BOTTOM
)


def gradient_bg():
    img = Image.new("RGB", (W, H))
    px = img.load()
    c0, c1, c2 = (249, 141, 176), (246, 158, 174), (241, 181, 180)
    for y in range(H):
        t = y / (H - 1)
        if t < 0.45:
            u = t / 0.45
            base = tuple(int(c0[i] + (c1[i] - c0[i]) * u) for i in range(3))
        else:
            u = (t - 0.45) / 0.55
            base = tuple(int(c1[i] + (c2[i] - c1[i]) * u) for i in range(3))
        for x in range(W):
            dx = (x - W * 0.5) / (W * 0.55)
            dy = (y - H * 0.1) / (H * 0.5)
            lift = max(0.0, 1.0 - (dx * dx + dy * dy)) * 28
            px[x, y] = tuple(
                min(255, int(base[i] + lift * (1 if i == 0 else 0.85 if i == 1 else 0.72)))
                for i in range(3)
            )
    return img


BG = gradient_bg()


def ink_offset(text, fnt):
    """Geometric center via textbbox (avoids clipped raster scratch pads)."""
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=fnt)
    return float((bbox[0] + bbox[2]) / 2), float((bbox[1] + bbox[3]) / 2)


def ink_size(text, fnt):
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered(d, cx, cy, text, fnt, fill):
    # Pillow middle-middle anchor — true optical center of the glyph box
    d.text((cx, cy), text, font=fnt, fill=fill, anchor="mm")


def shadow_panel(w, h, radius=20):
    pad = 28
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle(
        [pad, pad + 8, pad + w + 4, pad + h + 10],
        radius=radius + 2,
        fill=(60, 35, 70, 50),
    )
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    out = Image.alpha_composite(out, sh)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=(255, 255, 255, 255))
    return out, pad


def draw_steps(d, ox, oy, active):
    """Quiet progress chrome — active is the only strong signal."""
    steps = ["Variants", "Testing", "Results"]
    x = ox
    hpad, vpad = 16, 10
    ph_used = 36
    for i, label in enumerate(steps):
        on = i == active
        text = f"{i + 1}  {label}"
        iw, ih = ink_size(text, f_step)
        pw = iw + hpad * 2
        ph = max(36, ih + vpad * 2)
        ph_used = ph
        if on:
            fill_bg, fill_fg = (28, 26, 32), "white"
        else:
            fill_bg, fill_fg = MUTED_BG, INK_3
        d.rounded_rectangle([x, oy, x + pw, oy + ph], radius=ph // 2, fill=fill_bg)
        draw_centered(d, x + pw / 2, oy + ph / 2, text, f_step, fill_fg)
        x += pw + 8
    return ph_used


def steps_width(active=0):
    """Total width of the step pill row (including gaps)."""
    steps = ["Variants", "Testing", "Results"]
    hpad = 16
    total = 0
    for i, label in enumerate(steps):
        text = f"{i + 1}  {label}"
        iw, _ = ink_size(text, f_step)
        total += iw + hpad * 2
        if i < len(steps) - 1:
            total += 8
    return total


def wrap_centered_lines(text, fnt, max_w):
    """Word-wrap text to max_w; returns list of lines that each fit."""
    words = text.split()
    lines, cur = [], ""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for word in words:
        test = f"{cur} {word}".strip()
        bb = probe.textbbox((0, 0), test, font=fnt)
        if bb[2] - bb[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


def _fill_rgba(fill):
    if isinstance(fill, str):
        return (255, 255, 255, 255) if fill == "white" else (0, 0, 0, 255)
    if len(fill) == 3:
        return fill + (255,)
    return fill


def blit_centered_text(card, cx, cy, text, fnt, fill):
    """Rasterize text and paste so its ink bbox is exactly centered on (cx, cy)."""
    fill_rgba = _fill_rgba(fill)
    scratch = Image.new("RGBA", (1200, 200), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scratch)
    sd.text((600, 100), text, font=fnt, fill=fill_rgba, anchor="mm")
    bbox = scratch.getbbox()
    if not bbox:
        return
    cropped = scratch.crop(bbox)
    x = int(round(cx - cropped.width / 2))
    y = int(round(cy - cropped.height / 2))
    card.alpha_composite(cropped, (x, y))


def blit_letter_in_badge(card, cx, cy, letter, fnt, fill):
    """Center A/B in the circle by ink bbox (true geometric center of the glyph)."""
    fill_rgba = _fill_rgba(fill)
    scratch = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(scratch).text((100, 100), letter, font=fnt, fill=fill_rgba, anchor="mm")
    bbox = scratch.getbbox()
    if not bbox:
        return
    cropped = scratch.crop(bbox)
    # +1 x: Arial Bold caps lean slightly left of their ink center in tight circles
    x = int(round(cx + 1 - cropped.width / 2))
    y = int(round(cy - cropped.height / 2))
    card.alpha_composite(cropped, (x, y))


def blit_top_centered_text(card, cx, top_y, text, fnt, fill):
    """Horizontally center text; align the top of the ink to top_y."""
    fill_rgba = _fill_rgba(fill)
    scratch = Image.new("RGBA", (1200, 200), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scratch)
    sd.text((600, 100), text, font=fnt, fill=fill_rgba, anchor="mm")
    bbox = scratch.getbbox()
    if not bbox:
        return 0
    cropped = scratch.crop(bbox)
    x = int(round(cx - cropped.width / 2))
    y = int(round(top_y))
    card.alpha_composite(cropped, (x, y))
    return cropped.height


def make_variant_card(w, h, letter, tint, subject, opens=None, status="draft"):
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle(
        [0, 0, w - 1, h - 1],
        radius=16,
        fill=(255, 255, 255, 255),
        outline=LINE + (255,),
        width=1,
    )
    # Color accent — identity, not decoration overload
    d.rounded_rectangle([0, 0, w - 1, 8], radius=16, fill=tint + (255,))
    d.rectangle([0, 4, w - 1, 8], fill=tint + (255,))

    cx = w // 2
    pad_x = 16
    max_text_w = w - pad_x * 2
    br = VC_BADGE_R
    # Honor explicit line breaks; otherwise wrap to max width
    if "\n" in subject:
        lines = [ln.strip() for ln in subject.split("\n") if ln.strip()]
    else:
        lines = wrap_centered_lines(subject, f_subj, max_text_w)

    # Fixed Y slots — identical on A and B, every frame
    badge_y = VC_PAD_TOP
    subj_top = badge_y + br * 2 + VC_GAP_BADGE_SUBJ
    metrics_top = subj_top + VC_SUBJ_LINE * VC_SUBJ_LINES + VC_GAP_TO_METRICS
    pct_top = metrics_top + 14 + VC_GAP_LABEL_PCT

    badge_cx, badge_cy = cx, badge_y + br
    d.ellipse(
        [badge_cx - br, badge_y, badge_cx + br, badge_y + br * 2],
        fill=tint + (255,),
    )
    blit_letter_in_badge(card, badge_cx, badge_cy, letter, f_letter, "white")

    y = subj_top
    for line in lines[:VC_SUBJ_LINES]:
        blit_top_centered_text(card, cx, y, line, f_subj, INK)
        y += VC_SUBJ_LINE

    if opens is not None:
        blit_top_centered_text(card, cx, metrics_top, "OPEN RATE", f_metric_lbl, INK_3)
        blit_top_centered_text(card, cx, pct_top, opens, f_metric, INK)

    return card


def fade_card(card, opacity=0.34):
    grey = card.convert("LA").convert("RGBA")
    mixed = Image.blend(card, grey, 0.9)
    r, g, b, a = mixed.split()
    a = a.point(lambda p: int(p * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def make_scene(step):
    # Equal inset; panel width hugs the A/B variant cards
    PAD = 28
    gap = 16
    # Narrower A/B cards — more air around the pair inside the modal
    vw = int(((500 - PAD * 2 - gap) // 2) * 0.95)
    vh = VC_H  # height from spacing scale — equal pad top/bottom, no orphan gap
    cw = PAD * 2 + vw * 2 + gap  # hug the variant pair

    titles = [
        "Test two subject lines",
        "See which gets more opens",
        "Send the winner to everyone",
    ]

    title = "Email A/B test"
    # Extra air above the product title
    TOP_PAD = 48
    title_bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), title, font=f_h)
    title_ink_top = title_bbox[1]
    title_draw_y = TOP_PAD - title_ink_top
    title_ink_h = title_bbox[3] - title_bbox[1]

    pills_y = title_draw_y + title_ink_top + title_ink_h + 36
    _tmp = Image.new("RGBA", (1, 1))
    ph = draw_steps(ImageDraw.Draw(_tmp), 0, 0, step)

    rule_y = pills_y + ph + 22
    subtitle_y = rule_y + 20
    y0 = subtitle_y + 40
    content_bottom = y0 + vh
    ch = content_bottom + PAD

    card, pad = shadow_panel(cw, ch, 20)
    d = ImageDraw.Draw(card)
    ox, oy = pad, pad

    title_draw_y += oy
    pills_y += oy
    rule_y += oy
    subtitle_y += oy
    y0 += oy

    # Center product title + step pills + scene subtitle in the panel
    title_cx = ox + cw // 2
    title_cy = int(round(title_draw_y + title_ink_top + title_ink_h / 2))
    blit_centered_text(card, title_cx, title_cy, title, f_h, INK)

    pills_w = steps_width(step)
    draw_steps(d, ox + (cw - pills_w) // 2, pills_y, step)

    d.line([(ox + PAD, rule_y), (ox + cw - PAD, rule_y)], fill=LINE, width=1)
    sub = titles[step]
    _, sh = ink_size(sub, f_scene)
    blit_centered_text(card, title_cx, int(round(subtitle_y + sh / 2)), sub, f_scene, INK_2)

    left = ox + PAD
    right = left + vw + gap

    a_subj = "You're in —\nstart here"
    b_subj = "Welcome\naboard!"
    tint_a, tint_b = (120, 90, 220), (224, 121, 74)

    if step == 0:
        card.alpha_composite(
            make_variant_card(vw, vh, "A", tint_a, a_subj, status="draft"), (left, y0)
        )
        card.alpha_composite(
            make_variant_card(vw, vh, "B", tint_b, b_subj, status="draft"), (right, y0)
        )
    elif step == 1:
        card.alpha_composite(
            make_variant_card(vw, vh, "A", tint_a, a_subj, opens="24%", status="testing"),
            (left, y0),
        )
        card.alpha_composite(
            make_variant_card(vw, vh, "B", tint_b, b_subj, opens="18%", status="testing"),
            (right, y0),
        )
    else:
        card.alpha_composite(
            make_variant_card(vw, vh, "A", tint_a, a_subj, opens="24%", status="winner"),
            (left, y0),
        )
        card.alpha_composite(
            fade_card(
                make_variant_card(vw, vh, "B", tint_b, b_subj, opens="18%", status="sent"),
                0.34,
            ),
            (right, y0),
        )
    return card

scenes = [make_scene(0), make_scene(1), make_scene(2)]
HOLD0, HOLD1, HOLD2 = int(FPS * 2.2), int(FPS * 2.4), int(FPS * 3.0)


def place(scene):
    frame = BG.copy().convert("RGBA")
    frame.alpha_composite(scene, ((W - scene.width) // 2, (H - scene.height) // 2 - 6))
    return frame.convert("RGB")


p0, p1, p2 = place(scenes[0]), place(scenes[1]), place(scenes[2])
rgb = [p0, p1, p2]
durs = [
    int(1000 / FPS * HOLD0),
    int(1000 / FPS * HOLD1),
    int(1000 / FPS * HOLD2),
]
q = [
    f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    for f in rgb
]
q[0].save(
    OUT,
    save_all=True,
    append_images=q[1:],
    duration=durs,
    loop=0,
    optimize=False,
    disposal=2,
)
print("wrote", round(OUT.stat().st_size / 1024), "KB")

card_w = 520
card_h = int(card_w * H / W)
for name, frame in [("s0", p0), ("s1", p1), ("s2", p2)]:
    frame.resize((card_w, card_h), Image.Resampling.LANCZOS).save(
        Path(__file__).resolve().parent / f"_preview-card-{name}.png"
    )
p0.resize((720, 450), Image.Resampling.LANCZOS).save(PREVIEW)
print("previews ok")
