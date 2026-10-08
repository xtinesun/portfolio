"""CS2 case-study hero — high-res product UI, focused A/B story, refined chrome."""
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT_MP4 = ROOT / "cs2-hero.mp4"
OUT_MP4_BUST = ROOT / "cs2-hero-v63.mp4"
OUT_POSTER = ROOT / "cs2-hero-poster.png"
PREVIEW = ROOT / "_preview-cs2-hero-s0.png"

# 2× native SVG (2730×1254)
W, H = 5460, 2508
FPS = 16
S = H / 1080

INK = (18, 16, 22)
INK_3 = (120, 114, 106)
MUTED = (242, 240, 236)

SOURCES = [
    ROOT / "_svg_hi" / "hi-01.png",
    ROOT / "_svg_hi" / "hi-02.png",
    ROOT / "_svg_hi" / "hi-03.png",
]

SCENES = [0, 1, 2]  # active pill: Variants → Testing → Results
HOLDS = [2.0, 2.2, 2.5]  # static hold per scene (seconds)
TRANS = 1.0  # accordion expand/morph between scenes

# Accordion split: below parent A/B row; lower = top of "Happy to have you"
SPLIT_Y = 1376
LOWER_Y = [1780, 2020, 2016]
# White card interior (pink gutters live outside — never fill those with white)
CARD_X0, CARD_X1 = 860, 4600


def sx(v):
    return int(round(v * S))


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


f_step = font("Arial Bold", sx(22))


def ink_size(text, fnt):
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def load_base(step):
    im = Image.open(SOURCES[step]).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.Resampling.LANCZOS)
    return im


def white_bounds(arr):
    white = (arr[:, :, 0] > 248) & (arr[:, :, 1] > 248) & (arr[:, :, 2] > 248)
    rows = np.where(white.mean(axis=1) > 0.35)[0]
    top = int(rows[0]) if len(rows) else sx(292)
    mid_y = min(top + sx(80), H - 1)
    cols = np.where(white[mid_y])[0]
    left = int(cols[0]) if len(cols) else int(W * 0.12)
    right = int(cols[-1]) if len(cols) else int(W * 0.88)
    return top, left, right


def remove_floating_icons(im):
    """Rebuild pink outside the white card so decorative icons are gone."""
    arr = np.asarray(im).astype(np.float32)
    top, left, right = white_bounds(arr.astype(np.uint8))

    shadow_x = sx(28)
    card_x0 = max(0, left - shadow_x)
    card_x1 = min(W, right + shadow_x + 1)

    margin = sx(40)
    left_strip = arr[:, sx(8) : margin].mean(axis=1)
    right_strip = arr[:, W - margin : W - sx(8)].mean(axis=1)

    def clean_strip(strip):
        out = strip.copy()
        bright = out.mean(axis=1) > 230
        for y in range(H):
            if not bright[y]:
                continue
            fixed = False
            for dy in range(1, sx(40)):
                for yy in (y - dy, y + dy):
                    if 0 <= yy < H and not bright[yy]:
                        out[y] = out[yy]
                        fixed = True
                        break
                if fixed:
                    break
            if not fixed:
                out[y] = np.array([246, 150, 175], dtype=np.float32)
        return out

    left_strip = clean_strip(left_strip)
    right_strip = clean_strip(right_strip)

    xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    pink = left_strip[:, None, :] * (1 - xs) + right_strip[:, None, :] * xs

    yy = np.arange(H)[:, None]
    xx = np.arange(W)[None, :]
    keep = (yy >= top) & (xx >= card_x0) & (xx < card_x1)
    out = pink.copy()
    out[keep] = arr[keep]

    seam = max(0, top - sx(10))
    if top > seam:
        blend = np.linspace(0, 1, top - seam, dtype=np.float32)[:, None, None]
        out[seam:top] = out[seam:top] * (1 - blend) + arr[seam:top] * blend

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def steps_width():
    """Total width of the segmented control (including outer track pad)."""
    hpad = sx(22)
    gap = sx(4)
    track_pad = sx(6)
    total = track_pad * 2
    for i, label in enumerate(["Variants", "Testing", "Results"]):
        iw, _ = ink_size(label, f_step)
        total += iw + hpad * 2
        if i < 2:
            total += gap
    return total


def draw_steps(d, ox, oy, active, surface=None):
    """
    Segmented control — one soft track, active segment filled.
    Reads as progress without competing with the product UI.
    """
    labels = ["Variants", "Testing", "Results"]
    hpad = sx(22)
    gap = sx(4)
    track_pad = sx(6)
    ph = sx(48)
    track_h = ph + track_pad * 2

    # Measure segment widths
    widths = []
    for label in labels:
        iw, _ = ink_size(label, f_step)
        widths.append(iw + hpad * 2)
    track_w = track_pad * 2 + sum(widths) + gap * (len(labels) - 1)

    # Soft frosted track (works on pink)
    d.rounded_rectangle(
        [ox, oy, ox + track_w, oy + track_h],
        radius=track_h // 2,
        fill=(255, 255, 255, 210) if surface == "rgba" else (255, 255, 255),
    )

    x = ox + track_pad
    seg_y = oy + track_pad
    for i, label in enumerate(labels):
        pw = widths[i]
        on = i == active
        if on:
            d.rounded_rectangle(
                [x, seg_y, x + pw, seg_y + ph],
                radius=ph // 2,
                fill=(28, 26, 32),
            )
        d.text(
            (x + pw / 2, seg_y + ph / 2),
            label,
            font=f_step,
            fill="white" if on else INK_3,
            anchor="mm",
        )
        x += pw + gap
    return track_h, track_w


def make_scene(step):
    """Product UI only — step control is an HTML overlay for micro-interaction."""
    base = remove_floating_icons(load_base(step))
    return base.convert("RGB")


def ease_out_cubic(t):
    return 1.0 - (1.0 - t) ** 3


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def _nest_safe_cuts(nest, ha, hb):
    """Heights where the nest is mostly empty white — safe expand snap points."""
    if nest.shape[0] < hb:
        hb = nest.shape[0]
    gray = nest.mean(axis=(1, 2))
    ink = (
        (nest[:, :, 0] < 90) & (nest[:, :, 1] < 90) & (nest[:, :, 2] < 90)
    ).mean(axis=1)
    cuts = [ha]
    for y in range(ha + 12, hb - 12):
        if ink[y] < 0.003 and gray[y] > 247:
            if y - cuts[-1] >= 36:
                cuts.append(int(y))
    if cuts[-1] != hb:
        cuts.append(hb)
    # Always include a midpoint if we only have endpoints (no detected gaps)
    if len(cuts) == 2:
        mid = (ha + hb) // 2
        cuts = [ha, mid, hb]
    return cuts


def accordion_morph(a_img, b_img, split, lower_a, lower_b, t):
    """
    Variants→Testing expand:
      - Hold SOURCE nest + chrome while height grows (white gap below)
      - Late settle: crossfade full nest + parent chrome to destination

    Testing→Results (near-equal height): soft content crossfade only.

    Results→Variants collapse:
      - Clip SOURCE nest from the bottom (remove rows)
      - Settle to destination at the end
    """
    a = np.asarray(a_img).astype(np.float32)
    b = np.asarray(b_img).astype(np.float32)
    ha, hb = lower_a - split, lower_b - split
    nest_a = a[split:lower_a]
    nest_b = b[split:lower_b]
    delta = hb - ha

    def card_fill(nest):
        """Median card-interior color (excludes pink gutters)."""
        if nest is None or nest.shape[0] < 2:
            return np.array([255.0, 255.0, 255.0], dtype=np.float32)
        y0 = max(0, nest.shape[0] // 3)
        y1 = max(y0 + 1, (2 * nest.shape[0]) // 3)
        patch = nest[y0:y1, CARD_X0:CARD_X1]
        return np.median(patch.reshape(-1, 3), axis=0).astype(np.float32)

    def fill_from(nest):
        return card_fill(nest)

    def fit_h(nest, height, fill_nest):
        out = np.empty((height, W, 3), dtype=np.float32)
        take = min(height, nest.shape[0])
        out[:take] = nest[:take]
        if height > take:
            # Preserve gutters from last row; fill only card interior
            out[take:height] = nest[take - 1] if take else nest[0]
            out[take:height, CARD_X0:CARD_X1] = card_fill(fill_nest)
        return out

    def seed_mid(src, height):
        """Nest-height band from src so pink gutters stay correct."""
        out = np.empty((height, W, 3), dtype=np.float32)
        chunk = src[split : split + height]
        take = chunk.shape[0]
        out[:take] = chunk
        if take < height:
            out[take:height] = src[min(split + take - 1, H - 1)]
        return out

    def lower_band(src, lower, nest_for_fill, rem):
        chunk = src[lower : lower + rem]
        if chunk.shape[0] < rem:
            pad = np.empty((rem - chunk.shape[0], W, 3), dtype=np.float32)
            last = chunk[-1] if chunk.shape[0] else src[min(lower, H - 1)]
            pad[:] = last
            pad[:, CARD_X0:CARD_X1] = card_fill(
                nest_for_fill if chunk.shape[0] == 0 else chunk
            )
            chunk = np.concatenate([chunk, pad], axis=0)
        return chunk[:rem]

    # Near-equal height (Testing ↔ Results): soft crossfade, no accordion
    if abs(delta) <= 32:
        h = max(ha, hb)
        h = max(1, min(h, H - split - 8))
        ct = ease_in_out_cubic(t)
        top = a[:split] * (1.0 - ct) + b[:split] * ct
        mid = fit_h(nest_a, h, nest_a) * (1.0 - ct) + fit_h(nest_b, h, nest_b) * ct
        rem = H - (split + h)
        bot = (
            lower_band(a, lower_a, nest_a, rem) * (1.0 - ct)
            + lower_band(b, lower_b, nest_b, rem) * ct
        )
        out = np.concatenate([top, mid, bot], axis=0)
        if out.shape[0] < H:
            pad = np.empty((H - out.shape[0], W, 3), dtype=np.float32)
            pad[:] = out[-1]
            out = np.concatenate([out, pad], axis=0)
        return Image.fromarray(np.clip(out[:H], 0, 255).astype(np.uint8))

    te = ease_in_out_cubic(t)
    h = int(round(ha + delta * te))
    h = max(1, min(h, H - split - 8))
    settle = smoothstep((t - 0.86) / 0.14) if t > 0.86 else 0.0

    # Parent chrome / list-below: hold source through nest white-flash, then snap
    chrome_t = 0.0 if settle < 0.5 else 1.0
    top = a[:split] if chrome_t < 0.5 else b[:split]

    mid = seed_mid(a, h)

    if delta > 0:
        # EXPAND: hold source nest; open card-white below (keep pink gutters).
        # Testing nest is a full rewrite — never splice nest_b[ha:].
        base_h = min(h, ha, nest_a.shape[0])
        mid[:base_h, CARD_X0:CARD_X1] = nest_a[:base_h, CARD_X0:CARD_X1]
        if h > base_h:
            mid[base_h:h, CARD_X0:CARD_X1] = card_fill(nest_a)
    else:
        # COLLAPSE: clip source nest from the bottom (remove rows only)
        take = min(h, nest_a.shape[0])
        mid[:take, CARD_X0:CARD_X1] = nest_a[:take, CARD_X0:CARD_X1]
        if h > take:
            mid[take:h, CARD_X0:CARD_X1] = card_fill(nest_a)

    if settle > 0.0:
        # Dissolve card interior through white; gutters untouched
        white_mid = mid.copy()
        white_mid[:, CARD_X0:CARD_X1] = card_fill(nest_a if delta > 0 else nest_b)
        dst_mid = seed_mid(b, h)
        dst_fit = fit_h(nest_b, h, nest_b)
        dst_mid[:, CARD_X0:CARD_X1] = dst_fit[:, CARD_X0:CARD_X1]
        if settle < 0.5:
            u = settle * 2.0
            mid = mid * (1.0 - u) + white_mid * u
        else:
            u = (settle - 0.5) * 2.0
            mid = white_mid * (1.0 - u) + dst_mid * u

    rem = H - (split + h)
    bot = (
        lower_band(a, lower_a, nest_a, rem)
        if chrome_t < 0.5
        else lower_band(b, lower_b, nest_b, rem)
    )

    out = np.concatenate([top, mid, bot], axis=0)
    if out.shape[0] < H:
        pad = np.empty((H - out.shape[0], W, 3), dtype=np.float32)
        pad[:] = out[-1]
        out = np.concatenate([out, pad], axis=0)
    return Image.fromarray(np.clip(out[:H], 0, 255).astype(np.uint8))


def transition_frames(a_img, b_img, split, lower_a, lower_b, seconds):
    n = max(2, int(round(FPS * seconds)))
    frames = []
    for i in range(n):
        u = (i + 1) / n
        t = ease_in_out_cubic(u)
        frames.append(accordion_morph(a_img, b_img, split, lower_a, lower_b, t))
    return frames


def write_mp4(frames, path):
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, frame in enumerate(frames):
            frame.save(tmp / f"f{i:04d}.png", compress_level=1)
        cmd = [
            ffmpeg,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(tmp / "f%04d.png"),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "15",
            "-movflags",
            "+faststart",
            str(path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)


def main():
    scenes = [make_scene(i) for i in range(3)]
    frames = []

    # hold0 → expand testing → hold1 → morph results → hold2
    # → collapse back to variants (seamless loop)
    frames.extend([scenes[0]] * max(1, int(round(FPS * HOLDS[0]))))
    frames.extend(
        transition_frames(
            scenes[0], scenes[1], SPLIT_Y, LOWER_Y[0], LOWER_Y[1], TRANS
        )
    )
    frames.extend([scenes[1]] * max(1, int(round(FPS * HOLDS[1]))))
    frames.extend(
        transition_frames(
            scenes[1], scenes[2], SPLIT_Y, LOWER_Y[1], LOWER_Y[2], TRANS
        )
    )
    frames.extend([scenes[2]] * max(1, int(round(FPS * HOLDS[2]))))
    frames.extend(
        transition_frames(
            scenes[2], scenes[0], SPLIT_Y, LOWER_Y[2], LOWER_Y[0], TRANS
        )
    )

    # Pill-active durations (incoming transition counts toward next scene).
    # Closing Results→Variants collapse is handled in HTML via data-loop-trans.
    pill_holds = [
        HOLDS[0],
        TRANS + HOLDS[1],
        TRANS + HOLDS[2],
    ]

    write_mp4(frames, OUT_MP4)
    import shutil
    shutil.copy2(OUT_MP4, OUT_MP4_BUST)
    print("also", OUT_MP4_BUST.name)
    scenes[0].save(OUT_POSTER, optimize=True)
    pw = 1200
    for i, s in enumerate(scenes):
        s.resize((pw, int(pw * H / W)), Image.Resampling.LANCZOS).save(
            ROOT / f"_preview-cs2-hero-s{i}.png"
        )
    scenes[0].resize((pw, int(pw * H / W)), Image.Resampling.LANCZOS).save(PREVIEW)
    print(
        "wrote",
        OUT_MP4.name,
        round(OUT_MP4.stat().st_size / 1024),
        "KB",
        f"{W}x{H}",
        "frames",
        len(frames),
        "pill_holds",
        ",".join(f"{h:.2f}" for h in pill_holds),
    )


if __name__ == "__main__":
    main()
