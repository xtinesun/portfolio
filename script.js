"use strict";

const header = document.querySelector("[data-header]");
const revealEls = document.querySelectorAll("[data-reveal]");
const yearEl = document.querySelector("[data-year]");
const scrollProgress = document.querySelector("[data-scroll-progress]");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

document.body.classList.add("is-entering");
requestAnimationFrame(() => {
  document.body.classList.remove("is-entering");
  document.body.classList.add("is-entered");
});

if (yearEl) {
  yearEl.textContent = String(new Date().getFullYear());
}

document.querySelectorAll("video[data-playback-rate], video[data-end-pause]").forEach((video) => {
  const rate = Number.parseFloat(video.getAttribute("data-playback-rate") || "");
  const endPauseMs = Number.parseFloat(video.getAttribute("data-end-pause") || "");
  const applyRate = () => {
    if (Number.isFinite(rate) && rate > 0) video.playbackRate = rate;
  };
  applyRate();
  video.addEventListener("loadedmetadata", applyRate);
  video.addEventListener("play", applyRate);

  if (Number.isFinite(endPauseMs) && endPauseMs > 0) {
    video.loop = false;
    let restartTimer = 0;
    video.addEventListener("ended", () => {
      window.clearTimeout(restartTimer);
      restartTimer = window.setTimeout(() => {
        video.currentTime = 0;
        applyRate();
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(() => {});
        }
      }, endPauseMs);
    });
  }
});

/* CS2 hero — sync step pills to video scenes (display only) */
document.querySelectorAll("[data-cs2-hero]").forEach((hero) => {
  const video = hero.querySelector("[data-cs2-hero-video]");
  const track = hero.querySelector(".cs2-hero-steps__track");
  const thumb = hero.querySelector(".cs2-hero-steps__thumb");
  const segs = [...hero.querySelectorAll(".cs2-hero-steps__seg")];
  if (!video || !track || !thumb || segs.length < 3) return;

  const holds = (video.getAttribute("data-scene-holds") || "2.0,3.2,3.5")
    .split(",")
    .map((v) => Number.parseFloat(v.trim()))
    .filter((v) => Number.isFinite(v) && v > 0);
  if (holds.length !== 3) return;

  const loopTrans = Number.parseFloat(video.getAttribute("data-loop-trans") || "0");
  const edges = holds.reduce((acc, hold, i) => {
    acc.push((acc[i] || 0) + hold);
    return acc;
  }, [0]);
  // After Results hold, accordion collapses back to Variants
  const loopStart = edges[3];

  let active = 0;

  const layoutThumb = (index) => {
    const seg = segs[index];
    if (!seg) return;
    const trackBox = track.getBoundingClientRect();
    const segBox = seg.getBoundingClientRect();
    // Position from track’s left edge (thumb CSS left is 0) so the black
    // pill is exactly centered on the active label — including track pad.
    const left = segBox.left - trackBox.left;
    thumb.style.width = `${segBox.width}px`;
    thumb.style.transform = `translateX(${left}px)`;
  };

  const setActive = (index) => {
    const next = Math.max(0, Math.min(segs.length - 1, index));
    if (next === active) {
      layoutThumb(next);
      return;
    }
    active = next;
    segs.forEach((seg, i) => {
      seg.classList.toggle("is-active", i === active);
    });
    layoutThumb(active);
  };

  const syncFromTime = () => {
    const t = video.currentTime || 0;
    let index = 0;
    // Closing collapse (Results → Variants) counts as Variants
    if (Number.isFinite(loopTrans) && loopTrans > 0 && t >= loopStart) index = 0;
    else if (t >= edges[2]) index = 2;
    else if (t >= edges[1]) index = 1;
    else index = 0;
    setActive(index);
  };

  video.addEventListener("timeupdate", syncFromTime);
  video.addEventListener("seeked", syncFromTime);
  video.addEventListener("play", syncFromTime);
  window.addEventListener("resize", () => layoutThumb(active), { passive: true });

  // Initial layout after fonts/layout settle so the thumb centers on labels
  const boot = () => {
    setActive(0);
    syncFromTime();
    layoutThumb(active);
  };
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => requestAnimationFrame(boot));
  } else {
    requestAnimationFrame(boot);
  }
});

function updateHeader() {
  if (!header) return;
  header.classList.toggle("is-scrolled", window.scrollY > 8);
}

function updateScrollProgress() {
  if (!scrollProgress) return;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = docHeight > 0 ? (window.scrollY / docHeight) * 100 : 0;
  scrollProgress.style.width = `${progress}%`;
}

window.addEventListener("scroll", () => {
  updateHeader();
  updateScrollProgress();
}, { passive: true });

updateHeader();
updateScrollProgress();

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    // Use a near-zero threshold so tall sections (e.g. Key decisions) still reveal
    // when any part enters the viewport — ratio thresholds fail on multi-thousand-px elements.
    { threshold: 0.01, rootMargin: "0px 0px -8% 0px" }
  );

  revealEls.forEach((el) => observer.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add("is-visible"));
}

function animateCount(el) {
  const raw = el.textContent.trim();
  const match = raw.match(/^([+−-]?)(\d+(?:\.\d+)?)(×|%)?/);
  if (!match) return;

  const prefix = match[1] === "−" ? "−" : match[1];
  const target = parseFloat(match[2]);
  const suffix = match[3] || "";
  const isDecimal = raw.includes(".");
  const duration = 900;
  const start = performance.now();

  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const value = target * eased;
    const display = isDecimal ? value.toFixed(1) : Math.round(value).toString();
    el.textContent = `${prefix}${display}${suffix}`;
    if (t < 1) requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}

if (!prefersReducedMotion && "IntersectionObserver" in window) {
  const countObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          countObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  document.querySelectorAll("[data-count]").forEach((el) => countObserver.observe(el));
}

const caseSections = document.querySelectorAll("[data-section]");
const caseNavLinks = document.querySelectorAll("[data-nav-link]");

if (caseSections.length && caseNavLinks.length && "IntersectionObserver" in window) {
  const navObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          caseNavLinks.forEach((link) => {
            link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
          });
        }
      });
    },
    { rootMargin: "-30% 0px -55% 0px", threshold: 0 }
  );

  caseSections.forEach((section) => navObserver.observe(section));
}

document.querySelectorAll("[data-page-link]").forEach((link) => {
  if (prefersReducedMotion) return;

  link.addEventListener("click", (event) => {
    const href = link.getAttribute("href");
    if (!href || href.startsWith("http") || href.startsWith("mailto") || href.endsWith(".pdf")) return;

    event.preventDefault();
    document.body.classList.add("is-leaving");
    window.setTimeout(() => {
      window.location.href = href;
    }, 220);
  });
});

/** Force file download to disk (browsers often open PDFs inline otherwise). */
document.querySelectorAll("a.resume-download, a[data-download-file]").forEach((link) => {
  link.addEventListener("click", async (event) => {
    const href = link.getAttribute("href");
    if (!href) return;

    event.preventDefault();
    const filename =
      link.getAttribute("download") ||
      href.split("/").pop()?.split("?")[0] ||
      "download";

    try {
      const response = await fetch(href, { cache: "no-store" });
      if (!response.ok) throw new Error(`Download failed (${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const temp = document.createElement("a");
      temp.href = url;
      temp.download = filename;
      temp.style.display = "none";
      document.body.appendChild(temp);
      temp.click();
      temp.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      // Fallback if fetch is blocked (e.g. some file:// contexts)
      const temp = document.createElement("a");
      temp.href = href;
      temp.download = filename;
      temp.rel = "noopener";
      document.body.appendChild(temp);
      temp.click();
      temp.remove();
    }
  });
});

const mediaModal = document.querySelector("[data-media-modal]");
const mediaModalImage = document.querySelector("[data-media-modal-image]");
const mediaModalVideo = document.querySelector("[data-media-modal-video]");
const mediaModalSplit = document.querySelector("[data-media-modal-split]");
const mediaModalSplitTop = document.querySelector("[data-media-modal-split-top]");
const mediaModalSplitNav = document.querySelector("[data-media-modal-split-nav]");
const mediaModalSplitMain = document.querySelector("[data-media-modal-split-main]");
const mediaModalSplitMainImage = document.querySelector("[data-media-modal-split-main-image]");
const mediaExpandTriggers = document.querySelectorAll("[data-media-expand]");

const PAN_ZOOM_MIN = 1;
const PAN_ZOOM_STOPS = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24];
let panZoomScale = 1;
let panBaseWidth = 800;
let panNativeWidth = 11200;
let panNativeHeight = 11200;
let panIsVector = false;
let panZoomControlsWired = false;
let panFitReady = false;
let panScrollWired = false;
let panSvgSrc = "";
let lastMediaTrigger = null;

function isVideoSrc(src, type) {
  if (type === "video") return true;
  return /\.(mp4|webm|ogg)(\?|$)/i.test(src || "");
}

function isSvgSrc(src) {
  return /\.svg(\?|$)/i.test(src || "");
}

function getPanViewportEl() {
  return mediaModal?.querySelector("[data-media-pan-viewport]") || null;
}

function getPanViewportSize() {
  const viewport = getPanViewportEl();
  if (!viewport) {
    return { w: Math.max(1, window.innerWidth), h: Math.max(1, window.innerHeight) };
  }
  return {
    w: Math.max(1, viewport.clientWidth),
    h: Math.max(1, viewport.clientHeight),
  };
}

/** Width at Fit — scale so the entire artboard fits in the viewport (contain). */
function getPanFitBaseWidth() {
  const { w: vw, h: vh } = getPanViewportSize();
  const pad = 24;
  const availW = Math.max(1, vw - pad * 2);
  const availH = Math.max(1, vh - pad * 2);
  const aspect = panNativeWidth > 0 ? panNativeHeight / panNativeWidth : 1;
  const heightIfFitWidth = availW * aspect;
  // Contain: shrink to whichever axis hits the viewport first.
  if (heightIfFitWidth <= availH) return Math.round(availW);
  return Math.max(1, Math.round(availH / aspect));
}

function lockPanFitBase() {
  const next = getPanFitBaseWidth();
  const { w: vw, h: vh } = getPanViewportSize();
  // Only lock once the pan viewport has real layout size.
  if (vw > 80 && vh > 80 && next > 40) {
    panBaseWidth = next;
    panFitReady = true;
    return true;
  }
  return false;
}

/** Max zoom: ~1 CSS px per design px so UI details are readable. */
function getPanZoomMax() {
  if (!panFitReady || panBaseWidth < 1) return 8;
  const toNative = panNativeWidth / panBaseWidth;
  return Math.min(24, Math.max(6, Number(toNative.toFixed(2))));
}

/** Zoom where a typical ~1280px design frame fills most of the viewport. */
function getPanDetailZoom() {
  const { w: vw } = getPanViewportSize();
  const designFrame = 1280;
  const cssAtFit = designFrame * (panBaseWidth / Math.max(1, panNativeWidth));
  if (cssAtFit <= 1) return Math.min(4, getPanZoomMax());
  // Aim for the frame to fill ~92% of the viewport width — readable and crisp.
  return Math.min(getPanZoomMax(), Math.max(2.5, (vw * 0.92) / cssAtFit));
}

function getPanZoomStops() {
  const max = getPanZoomMax();
  const stops = PAN_ZOOM_STOPS.filter((stop) => stop <= max + 0.001);
  if (stops[stops.length - 1] < max - 0.05) stops.push(max);
  return stops;
}

function nearestPanZoomStop(scale) {
  const stops = getPanZoomStops();
  return stops.reduce((best, stop) =>
    Math.abs(stop - scale) < Math.abs(best - scale) ? stop : best
  );
}

function stepPanZoom(direction, anchor) {
  const stops = getPanZoomStops();
  if (direction > 0) {
    const next = stops.find((stop) => stop > panZoomScale + 0.02);
    setPanZoom(next ?? getPanZoomMax(), anchor);
  } else {
    const prev = [...stops].reverse().find((stop) => stop < panZoomScale - 0.02);
    setPanZoom(prev ?? PAN_ZOOM_MIN, anchor);
  }
}

function getPanViewportCenterAnchor() {
  const viewport = getPanViewportEl();
  if (!viewport) return null;
  const rect = viewport.getBoundingClientRect();
  return {
    clientX: rect.left + viewport.clientWidth / 2,
    clientY: rect.top + viewport.clientHeight / 2,
  };
}

function whenPanViewportReady(callback) {
  let tries = 0;
  const tick = () => {
    const { w, h } = getPanViewportSize();
    if (w > 80 && h > 80) {
      callback();
      return;
    }
    tries += 1;
    if (tries < 30) requestAnimationFrame(tick);
    else callback();
  };
  requestAnimationFrame(tick);
}

function loadModalImage(img, src, options = {}) {
  if (!img || !src) return;
  const base = src.split("?")[0];
  const { onLoad } = options;
  img.removeAttribute("src");
  img.style.width = "";
  img.style.height = "";
  img.style.maxWidth = "";
  img.style.transform = "";
  img.style.transformOrigin = "";
  const handleLoad = () => {
    img.removeEventListener("load", handleLoad);
    if (typeof onLoad === "function") onLoad(img, src);
  };
  img.addEventListener("load", handleLoad);
  requestAnimationFrame(() => {
    img.src = `${base}?t=${Date.now()}`;
  });
}

function getPanZoomControls() {
  if (!mediaModal) return null;
  return mediaModal.querySelector("[data-media-pan-zoom]");
}

function ensurePanStage() {
  if (!mediaModal) return null;
  const dialog = mediaModal.querySelector(".media-modal-dialog");
  if (!dialog) return null;

  let viewport = dialog.querySelector("[data-media-pan-viewport]");
  if (!viewport) {
    viewport = document.createElement("div");
    viewport.className = "media-modal-pan-viewport";
    viewport.setAttribute("data-media-pan-viewport", "");
    const closeBtn = dialog.querySelector(".media-modal-close");
    if (closeBtn) dialog.insertBefore(viewport, closeBtn);
    else dialog.appendChild(viewport);
  }

  if (!panScrollWired) {
    panScrollWired = true;
    viewport.addEventListener(
      "scroll",
      () => {
        if (panIsVector) syncPanViewBoxFromScroll();
      },
      { passive: true }
    );
  }

  let sizer = viewport.querySelector("[data-media-pan-sizer]");
  if (!sizer) {
    sizer = document.createElement("div");
    sizer.className = "media-modal-pan-sizer";
    sizer.setAttribute("data-media-pan-sizer", "");
    viewport.appendChild(sizer);
  }

  let stage = sizer.querySelector("[data-media-pan-stage]");
  if (!stage) {
    stage = document.createElement("div");
    stage.className = "media-modal-pan-stage";
    stage.setAttribute("data-media-pan-stage", "");
    sizer.appendChild(stage);
  }
  return stage;
}

function ensurePanLens() {
  const dialog = mediaModal?.querySelector(".media-modal-dialog");
  if (!dialog) return null;
  let lens = dialog.querySelector("[data-media-pan-lens]");
  if (!lens) {
    lens = document.createElement("div");
    lens.className = "media-modal-pan-lens";
    lens.setAttribute("data-media-pan-lens", "");
    lens.setAttribute("aria-hidden", "true");
    const viewport = dialog.querySelector("[data-media-pan-viewport]");
    if (viewport) dialog.insertBefore(lens, viewport);
    else {
      const closeBtn = dialog.querySelector(".media-modal-close");
      if (closeBtn) dialog.insertBefore(lens, closeBtn);
      else dialog.appendChild(lens);
    }
  }
  return lens;
}

function ensurePanHiresMount() {
  const lens = ensurePanLens();
  if (!lens) return null;
  let mount = lens.querySelector("[data-media-pan-hires]");
  if (!mount) {
    mount = document.createElement("div");
    mount.className = "media-modal-pan-hires";
    mount.setAttribute("data-media-pan-hires", "");
    lens.appendChild(mount);
  }
  return mount;
}

function getPanSvgRoot() {
  const lens = mediaModal?.querySelector("[data-media-pan-lens]");
  if (!lens) return null;
  // Prefer inlined SVG (crisp). Fall back to <object> contentDocument.
  const inline = lens.querySelector("svg[data-media-pan-svg]");
  if (inline) return inline;
  const frame = lens.querySelector("object[data-media-pan-svg], iframe[data-media-pan-svg]");
  if (!frame) return null;
  try {
    const doc = frame.contentDocument;
    if (!doc) return null;
    if (doc.documentElement?.tagName?.toLowerCase() === "svg") {
      return doc.documentElement;
    }
    return doc.querySelector("svg");
  } catch (_err) {
    return null;
  }
}

function getPanCrispDpr() {
  // Paint at least 2× so zoomed UI stays sharp on retina and 1× displays.
  return Math.min(3, Math.max(2, window.devicePixelRatio || 1));
}

function ensurePanCanvas() {
  // Deprecated path — canvas SVG-as-image softens/blank-paints huge Figma exports.
  return null;
}

function layoutPanHiresSurface() {
  const lens = mediaModal?.querySelector("[data-media-pan-lens]");
  const mount = mediaModal?.querySelector("[data-media-pan-hires]");
  const svg = getPanSvgRoot();
  if (!lens || !mount) return { cssW: 1, cssH: 1, dpr: 2 };

  const cssW = Math.max(1, lens.clientWidth || lens.offsetWidth);
  const cssH = Math.max(1, lens.clientHeight || lens.offsetHeight);
  const dpr = getPanCrispDpr();
  const paintW = Math.round(cssW * dpr);
  const paintH = Math.round(cssH * dpr);

  // CSS zoom (not transform) makes Chrome/Safari rasterize at paintW×paintH, then display at css size.
  mount.hidden = false;
  mount.style.opacity = "1";
  mount.style.width = `${paintW}px`;
  mount.style.height = `${paintH}px`;
  const supportsZoom =
    typeof CSS !== "undefined" &&
    typeof CSS.supports === "function" &&
    CSS.supports("zoom", "0.5");
  if (supportsZoom) {
    mount.style.zoom = String(1 / dpr);
    mount.style.transform = "";
  } else {
    mount.style.zoom = "";
    mount.style.transform = `scale(${1 / dpr})`;
    mount.style.transformOrigin = "0 0";
  }

  if (svg) {
    svg.setAttribute("width", String(paintW));
    svg.setAttribute("height", String(paintH));
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.display = "block";
  }

  // Ensure any leftover canvas is hidden.
  const canvas = mediaModal?.querySelector("[data-media-pan-canvas]");
  if (canvas) canvas.hidden = true;

  return { cssW, cssH, dpr, paintW, paintH };
}

let panPaintToken = 0;
let panPaintTimer = 0;
let panPaintUrl = "";

function schedulePanCrispPaint() {
  // Live SVG + CSS zoom is the crisp path; no deferred canvas paint needed.
}

/**
 * Crop the inline SVG via viewBox and paint it through a CSS-zoom hi-DPI mount.
 */
function syncPanViewBoxFromScroll() {
  if (!panIsVector || !panFitReady) return;
  const svg = getPanSvgRoot();
  const viewport = getPanViewportEl();
  const stage = mediaModal?.querySelector("[data-media-pan-stage]");
  if (!svg || !viewport || !stage) return;

  layoutPanHiresSurface();

  const visualW = Math.max(1, stage.offsetWidth || panBaseWidth * panZoomScale);
  const visualH = Math.max(
    1,
    stage.offsetHeight ||
      visualW * (panNativeWidth > 0 ? panNativeHeight / panNativeWidth : 1)
  );
  const stageLeft = Number.parseFloat(stage.style.left) || 0;
  const stageTop = Number.parseFloat(stage.style.top) || 0;
  const vw = Math.max(1, viewport.clientWidth);
  const vh = Math.max(1, viewport.clientHeight);

  // Fit (or stage fully visible): show the entire artboard, letterboxed.
  if (visualW <= vw + 1 && visualH <= vh + 1) {
    svg.setAttribute("viewBox", `0 0 ${panNativeWidth} ${panNativeHeight}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    return;
  }

  const left = Math.max(0, Math.min(viewport.scrollLeft - stageLeft, visualW));
  const top = Math.max(0, Math.min(viewport.scrollTop - stageTop, visualH));
  const width = Math.max(1, Math.min(vw, visualW - left));
  const height = Math.max(1, Math.min(vh, visualH - top));

  const vbX = (left / visualW) * panNativeWidth;
  const vbY = (top / visualH) * panNativeHeight;
  const vbW = (width / visualW) * panNativeWidth;
  const vbH = (height / visualH) * panNativeHeight;
  svg.setAttribute("viewBox", `${vbX} ${vbY} ${vbW} ${vbH}`);
  // Fill the lens exactly — scroll already defines the crop aspect.
  svg.setAttribute("preserveAspectRatio", "none");
}

function prepareInlinePanSvg(svg) {
  if (!svg) return;
  svg.setAttribute("data-media-pan-svg", "");
  svg.classList.add("media-modal-pan-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.setAttribute("shape-rendering", "geometricPrecision");
  svg.setAttribute("text-rendering", "geometricPrecision");
  svg.style.display = "block";
  svg.style.width = "100%";
  svg.style.height = "100%";
  svg.style.maxWidth = "none";
  svg.style.maxHeight = "none";
  svg.style.pointerEvents = "none";
  // Keep embedded bitmaps as sharp as possible when scaled.
  svg.querySelectorAll("image").forEach((img) => {
    img.setAttribute("image-rendering", "optimizeQuality");
    img.style.imageRendering = "auto";
  });
}

async function loadInlinePanSvg(src) {
  const mount = ensurePanHiresMount();
  const lens = ensurePanLens();
  if (!mount || !lens) return null;

  // Clear prior object/iframe/svg renderers.
  lens.querySelectorAll("object[data-media-pan-svg], iframe[data-media-pan-svg], svg[data-media-pan-svg]").forEach((el) => {
    el.remove();
  });
  mount.replaceChildren();

  const base = src.split("?")[0];
  const url = `${base}?t=${Date.now()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`SVG fetch failed: ${res.status}`);
  const text = await res.text();
  const doc = new DOMParser().parseFromString(text, "image/svg+xml");
  const svg = doc.querySelector("svg");
  if (!svg || doc.querySelector("parsererror")) {
    throw new Error("SVG parse failed");
  }

  // Adopt into the live document.
  const adopted = document.importNode(svg, true);
  prepareInlinePanSvg(adopted);
  if (!adopted.getAttribute("viewBox")) {
    const w = adopted.getAttribute("width") || panNativeWidth;
    const h = adopted.getAttribute("height") || panNativeHeight;
    adopted.setAttribute("viewBox", `0 0 ${parseFloat(w)} ${parseFloat(h)}`);
  }
  // Native size from the file when attrs missing on the trigger.
  const vb = adopted.getAttribute("viewBox")?.trim().split(/[\s,]+/);
  if (vb && vb.length === 4) {
    const vbW = Number(vb[2]);
    const vbH = Number(vb[3]);
    if (vbW > 0) panNativeWidth = vbW;
    if (vbH > 0) panNativeHeight = vbH;
  }

  mount.appendChild(adopted);
  layoutPanHiresSurface();
  return adopted;
}

function clearPanStageLayout() {
  if (mediaModalImage) {
    mediaModalImage.hidden = false;
    mediaModalImage.style.width = "";
    mediaModalImage.style.height = "";
    mediaModalImage.style.maxWidth = "";
    mediaModalImage.style.maxHeight = "";
    mediaModalImage.style.objectFit = "";
    mediaModalImage.style.transform = "";
    mediaModalImage.style.transformOrigin = "";
    mediaModalImage.style.pointerEvents = "";
  }
  const dialog = mediaModal?.querySelector(".media-modal-dialog");
  const stage = mediaModal?.querySelector("[data-media-pan-stage]");
  const sizer = mediaModal?.querySelector("[data-media-pan-sizer]");
  const viewport = mediaModal?.querySelector("[data-media-pan-viewport]");
  const lens = mediaModal?.querySelector("[data-media-pan-lens]");
  if (lens) lens.remove();
  if (stage && mediaModalImage && mediaModalImage.parentElement === stage && dialog) {
    const closeBtn = dialog.querySelector(".media-modal-close");
    dialog.insertBefore(mediaModalImage, closeBtn || null);
  } else if (dialog && mediaModalImage && mediaModalImage.parentElement !== dialog) {
    const closeBtn = dialog.querySelector(".media-modal-close");
    dialog.insertBefore(mediaModalImage, closeBtn || null);
  }
  if (stage) stage.remove();
  if (sizer) sizer.remove();
  if (viewport) viewport.remove();
  panIsVector = false;
  panFitReady = false;
  panSvgSrc = "";
}

function updatePanZoomLabel() {
  const label = mediaModal?.querySelector("[data-media-zoom-label]");
  if (label) {
    label.textContent =
      panZoomScale <= 1.001 ? "Fit" : `${Math.round(panZoomScale * 100)}%`;
  }
  const zoomInBtn = mediaModal?.querySelector("[data-media-zoom-in]");
  const zoomOutBtn = mediaModal?.querySelector("[data-media-zoom-out]");
  const max = getPanZoomMax();
  if (zoomInBtn) zoomInBtn.disabled = panZoomScale >= max - 0.02;
  if (zoomOutBtn) zoomOutBtn.disabled = panZoomScale <= PAN_ZOOM_MIN + 0.02;
  updatePanZoomCursor();
}

function updatePanZoomCursor() {
  const viewport = getPanViewportEl();
  if (!viewport) return;
  const atMax = panZoomScale >= getPanZoomMax() - 0.02;
  viewport.classList.toggle("is-zoom-out-cursor", atMax);
}

function applyPanZoom(anchor) {
  const dialog = mediaModal?.querySelector(".media-modal-dialog");
  const stage = ensurePanStage();
  const viewport = dialog?.querySelector("[data-media-pan-viewport]");
  const sizer = viewport?.querySelector("[data-media-pan-sizer]");
  if (!stage || !viewport || !sizer) return;

  if (!panFitReady && !lockPanFitBase()) return;

  const visualW = Math.max(1, Math.round(panBaseWidth * panZoomScale));
  const aspect =
    panNativeWidth > 0 ? panNativeHeight / panNativeWidth : 1;
  const visualH = Math.max(1, Math.round(visualW * aspect));

  const prevVisualW = Math.max(1, stage.offsetWidth || visualW);
  const prevVisualH = Math.max(1, stage.offsetHeight || visualH);
  const prevStageLeft = Number.parseFloat(stage.style.left) || 0;
  const prevStageTop = Number.parseFloat(stage.style.top) || 0;

  const vw = viewport.clientWidth;
  const vh = viewport.clientHeight;
  const rect = viewport.getBoundingClientRect();
  const localX = anchor ? anchor.clientX - rect.left : vw / 2;
  const localY = anchor ? anchor.clientY - rect.top : vh / 2;

  const focusInStageX = viewport.scrollLeft + localX - prevStageLeft;
  const focusInStageY = viewport.scrollTop + localY - prevStageTop;
  const fracX = Math.min(1, Math.max(0, focusInStageX / prevVisualW));
  const fracY = Math.min(1, Math.max(0, focusInStageY / prevVisualH));

  const sizerW = Math.max(vw, visualW);
  const sizerH = Math.max(vh, visualH);
  const stageLeft =
    visualW >= vw ? 0 : Math.round((sizerW - visualW) / 2);
  const stageTop =
    visualH >= vh ? 0 : Math.round((sizerH - visualH) / 2);

  sizer.style.width = `${sizerW}px`;
  sizer.style.height = `${sizerH}px`;
  stage.style.width = `${visualW}px`;
  stage.style.height = `${visualH}px`;
  stage.style.left = `${stageLeft}px`;
  stage.style.top = `${stageTop}px`;

  const lens = ensurePanLens();
  if (panIsVector) {
    // Vector path: transparent scroll surface + viewport-sized SVG lens (crisp at any zoom).
    if (lens) lens.hidden = false;
    stage.classList.add("is-vector-spacer");
    if (mediaModalImage) {
      mediaModalImage.hidden = true;
      if (mediaModalImage.parentElement === stage) {
        const closeBtn = dialog.querySelector(".media-modal-close");
        dialog.insertBefore(mediaModalImage, closeBtn || null);
      }
    }
    const legacyInStage = stage.querySelector("[data-media-pan-svg]");
    if (legacyInStage) legacyInStage.remove();
  } else {
    if (lens) lens.hidden = true;
    stage.classList.remove("is-vector-spacer");
    if (mediaModalImage) {
      if (mediaModalImage.parentElement !== stage) stage.appendChild(mediaModalImage);
      mediaModalImage.hidden = false;
      mediaModalImage.style.width = `${visualW}px`;
      mediaModalImage.style.height = `${visualH}px`;
      mediaModalImage.style.maxWidth = "none";
      mediaModalImage.style.maxHeight = "none";
      mediaModalImage.style.objectFit = "fill";
      mediaModalImage.style.objectPosition = "center";
      mediaModalImage.style.display = "block";
      mediaModalImage.style.pointerEvents = "none";
      mediaModalImage.style.imageRendering = "auto";
    }
  }

  updatePanZoomLabel();

  if (panZoomScale <= 1.001) {
    viewport.scrollLeft = Math.max(0, (sizerW - vw) / 2);
    viewport.scrollTop = Math.max(0, (sizerH - vh) / 2);
  } else {
    viewport.scrollLeft = stageLeft + fracX * visualW - localX;
    viewport.scrollTop = stageTop + fracY * visualH - localY;
  }

  if (panIsVector) syncPanViewBoxFromScroll();
}

function setPanZoom(nextScale, anchor) {
  const max = getPanZoomMax();
  const clamped = Math.min(max, Math.max(PAN_ZOOM_MIN, nextScale));
  if (Math.abs(clamped - panZoomScale) < 0.001) {
    updatePanZoomLabel();
    return;
  }
  panZoomScale = clamped;
  applyPanZoom(anchor);
}

function fitPanZoom() {
  panZoomScale = PAN_ZOOM_MIN;
  panFitReady = false;
  lockPanFitBase();
  applyPanZoom(getPanViewportCenterAnchor());
  updatePanZoomLabel();
}

function togglePanDetailZoom(anchor) {
  if (panZoomScale <= 1.15) {
    setPanZoom(nearestPanZoomStop(getPanDetailZoom()), anchor || getPanViewportCenterAnchor());
  } else {
    fitPanZoom();
  }
}

/** Open (or reset) fully zoomed out — entire artboard in one birds-eye view. */
function openPanBirdsEye() {
  panZoomScale = PAN_ZOOM_MIN;
  panFitReady = false;
  whenPanViewportReady(() => {
    lockPanFitBase();
    panZoomScale = PAN_ZOOM_MIN;
    applyPanZoom();
    positionPanZoomControls();
    // Re-measure after layout. Do NOT reset if the user already zoomed in.
    requestAnimationFrame(() => {
      if (panZoomScale > 1.001) {
        // User zoomed before this frame — only refresh base, keep scale.
        const keep = panZoomScale;
        panFitReady = false;
        lockPanFitBase();
        panZoomScale = keep;
        applyPanZoom();
        positionPanZoomControls();
        return;
      }
      panFitReady = false;
      lockPanFitBase();
      panZoomScale = PAN_ZOOM_MIN;
      applyPanZoom();
      positionPanZoomControls();
      if (panIsVector) syncPanViewBoxFromScroll();
    });
  });
}

function reflowPanFit({ resetScale = false } = {}) {
  if (resetScale) {
    openPanBirdsEye();
    return;
  }
  whenPanViewportReady(() => {
    const keep = panZoomScale;
    panFitReady = false;
    lockPanFitBase();
    panZoomScale = Math.min(keep, getPanZoomMax());
    applyPanZoom();
    positionPanZoomControls();
  });
}

function showPanZoomControls(show) {
  const controls = getPanZoomControls();
  if (!controls) return;
  controls.hidden = !show;
  if (show) {
    updatePanZoomLabel();
    positionPanZoomControls();
  } else {
    clearPanZoomPosition();
  }
}

function positionPanZoomControls() {
  const controls = getPanZoomControls();
  const dialog = mediaModal?.querySelector(".media-modal-dialog--pan");
  if (!controls || controls.hidden || !dialog) return;
  const rect = dialog.getBoundingClientRect();
  const padX = 16;
  const padY = 28;
  controls.style.position = "fixed";
  controls.style.left = `${Math.round(rect.left + padX)}px`;
  controls.style.bottom = `${Math.round(window.innerHeight - rect.bottom + padY)}px`;
  controls.style.top = "auto";
  controls.style.right = "auto";
  controls.style.zIndex = "220";
}

function clearPanZoomPosition() {
  const controls = getPanZoomControls();
  if (!controls) return;
  controls.style.left = "";
  controls.style.bottom = "";
  controls.style.top = "";
  controls.style.right = "";
  controls.style.position = "";
  controls.style.zIndex = "";
}

function normalizePanSvgDocument(frame) {
  // Legacy helper for object/iframe — kept for safety if something still uses them.
  try {
    const doc = frame?.contentDocument;
    const svg = doc?.documentElement?.tagName?.toLowerCase() === "svg"
      ? doc.documentElement
      : doc?.querySelector("svg");
    if (!svg) return false;
    prepareInlinePanSvg(svg);
    if (!svg.getAttribute("viewBox")) {
      const w = svg.getAttribute("width") || panNativeWidth;
      const h = svg.getAttribute("height") || panNativeHeight;
      svg.setAttribute("viewBox", `0 0 ${parseFloat(w)} ${parseFloat(h)}`);
    }
    if (doc?.body) {
      doc.body.style.margin = "0";
      doc.body.style.background = "#2a2a2a";
      doc.body.style.overflow = "hidden";
      doc.body.style.width = "100%";
      doc.body.style.height = "100%";
    }
    if (doc?.documentElement) {
      doc.documentElement.style.width = "100%";
      doc.documentElement.style.height = "100%";
      doc.documentElement.style.margin = "0";
    }
    return true;
  } catch (_err) {
    return false;
  }
}

function setupPanModalMedia(src, trigger) {
  const stage = ensurePanStage();
  if (!stage) return;

  const attrW = Number(trigger?.getAttribute("data-media-pan-width"));
  const attrH = Number(trigger?.getAttribute("data-media-pan-height"));
  const fallback = trigger?.getAttribute("data-media-fallback") || "";
  panIsVector = isSvgSrc(src);
  panFitReady = false;
  panZoomScale = PAN_ZOOM_MIN;
  panNativeWidth = attrW > 0 ? attrW : 24000;
  panNativeHeight = attrH > 0 ? attrH : panNativeWidth;
  panSvgSrc = src || "";

  let openedOnce = false;
  const afterReady = () => {
    if (!openedOnce) {
      openedOnce = true;
      openPanBirdsEye();
    } else {
      applyPanZoom();
    }
  };

  if (panIsVector) {
    // Inline SVG + DPR paint buffer so zoom stays vector-crisp.
    if (mediaModalImage) {
      mediaModalImage.hidden = true;
      mediaModalImage.removeAttribute("src");
    }
    const lens = ensurePanLens();
    if (lens) lens.hidden = false;
    stage.classList.add("is-vector-spacer");
    ensurePanHiresMount();

    loadInlinePanSvg(src)
      .then(() => {
        afterReady();
        requestAnimationFrame(() => {
          if (panZoomScale > 1.001) {
            syncPanViewBoxFromScroll();
            return;
          }
          afterReady();
        });
      })
      .catch(() => {
        // Fall back to <img> (may soft-upscale) or PNG.
        panIsVector = false;
        if (lens) lens.hidden = true;
        const rasterSrc = fallback || src;
        if (mediaModalImage) {
          loadModalImage(mediaModalImage, rasterSrc, {
            onLoad: (img) => {
              if (img?.naturalWidth > 0) {
                panNativeWidth = img.naturalWidth || panNativeWidth;
                panNativeHeight = img.naturalHeight || panNativeHeight;
              }
              afterReady();
            },
          });
        } else {
          afterReady();
        }
      });

    // Size the empty scroll surface immediately while the SVG loads.
    openPanBirdsEye();
    positionPanZoomControls();
    return;
  }

  // Raster fallback path (PNG).
  const lens = mediaModal?.querySelector("[data-media-pan-lens]");
  if (lens) lens.hidden = true;
  stage.classList.remove("is-vector-spacer");

  if (mediaModalImage && mediaModalImage.parentElement !== stage) {
    stage.appendChild(mediaModalImage);
  }

  if (!mediaModalImage) {
    openPanBirdsEye();
    return;
  }

  mediaModalImage.hidden = false;
  mediaModalImage.style.pointerEvents = "none";
  mediaModalImage.onerror = () => {
    if (!fallback) return;
    const fallbackBase = fallback.split("?")[0];
    if (mediaModalImage.src.includes(fallbackBase)) return;
    mediaModalImage.onerror = null;
    loadModalImage(mediaModalImage, fallback, {
      onLoad: (img) => {
        if (img?.naturalWidth > 0) {
          panNativeWidth = img.naturalWidth || panNativeWidth;
          panNativeHeight = img.naturalHeight || panNativeHeight;
        }
        afterReady();
      },
    });
  };
  loadModalImage(mediaModalImage, src, {
    onLoad: (img) => {
      if (img?.naturalWidth > 0) {
        panNativeWidth = img.naturalWidth || panNativeWidth;
        panNativeHeight = img.naturalHeight || panNativeHeight;
      }
      afterReady();
    },
  });

  const viewport = mediaModal?.querySelector("[data-media-pan-viewport]");
  if (viewport) {
    viewport.scrollTop = 0;
    viewport.scrollLeft = 0;
  }
  openPanBirdsEye();
  positionPanZoomControls();
}

function hideModalSplit() {
  if (!mediaModalSplit) return;
  mediaModalSplit.hidden = true;
  if (mediaModalSplitTop) {
    mediaModalSplitTop.removeAttribute("src");
    mediaModalSplitTop.alt = "";
  }
  if (mediaModalSplitNav) {
    mediaModalSplitNav.removeAttribute("src");
    mediaModalSplitNav.alt = "";
  }
  if (mediaModalSplitMainImage) {
    mediaModalSplitMainImage.removeAttribute("src");
    mediaModalSplitMainImage.alt = "";
  }
  if (mediaModalSplitMain) mediaModalSplitMain.scrollTop = 0;
}

function openMediaModal(trigger) {
  if (!mediaModal || !trigger) return;

  const src = trigger.getAttribute("data-media-src");
  const alt = trigger.getAttribute("data-media-alt") || "";
  const type = trigger.getAttribute("data-media-type") || "";
  const splitTopSrc = trigger.getAttribute("data-media-split-top");
  const splitNavSrc = trigger.getAttribute("data-media-split-nav");
  const splitMainSrc = trigger.getAttribute("data-media-split-main");
  const useSplit = Boolean(
    splitNavSrc &&
      splitMainSrc &&
      mediaModalSplit &&
      mediaModalSplitNav &&
      mediaModalSplitMainImage
  );
  if (!src && !useSplit) return;

  lastMediaTrigger = trigger;
  const useVideo = !useSplit && isVideoSrc(src, type) && mediaModalVideo;
  const mediaDialog = mediaModal.querySelector(".media-modal-dialog");
  const isTall = trigger.hasAttribute("data-media-scroll") && !useSplit;
  const isPan = trigger.hasAttribute("data-media-pan") && !useSplit;
  const isZoom = trigger.hasAttribute("data-media-zoom");
  const isHires =
    trigger.hasAttribute("data-media-hires") ||
    (!useSplit && /\.svg(\?|$)/i.test(src || ""));

  if (mediaDialog) {
    mediaDialog.classList.toggle("media-modal-dialog--tall", Boolean(isTall && !isPan && !useVideo));
    mediaDialog.classList.toggle("media-modal-dialog--pan", Boolean(isPan && !useVideo));
    mediaDialog.classList.toggle("media-modal-dialog--zoom", Boolean(isZoom && !useVideo));
    mediaDialog.classList.toggle("media-modal-dialog--split", Boolean(useSplit));
    mediaDialog.classList.toggle(
      "media-modal-dialog--hires",
      Boolean(isHires && !isPan && !isTall && !isZoom && !useSplit)
    );
    mediaDialog.classList.toggle("media-modal-dialog--video", Boolean(useVideo));
    mediaDialog.scrollTop = 0;
    mediaDialog.scrollLeft = 0;
  }

  showPanZoomControls(Boolean(isPan && !useVideo));
  if (isPan) {
    panZoomScale = PAN_ZOOM_MIN;
    panFitReady = false;
    updatePanZoomLabel();
    requestAnimationFrame(() => {
      positionPanZoomControls();
      requestAnimationFrame(positionPanZoomControls);
    });
  }

  if (useVideo) {
    hideModalSplit();
    if (mediaModalImage) {
      mediaModalImage.hidden = true;
      mediaModalImage.removeAttribute("src");
      mediaModalImage.alt = "";
    }
    mediaModalVideo.hidden = false;
    mediaModalVideo.setAttribute("aria-label", alt);
    mediaModalVideo.poster = trigger.getAttribute("data-media-poster") || "";
    mediaModalVideo.src = src;
    mediaModalVideo.muted = true;
    mediaModalVideo.loop = true;
    mediaModalVideo.playsInline = true;
    const playPromise = mediaModalVideo.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {});
    }
  } else if (useSplit) {
    if (mediaModalVideo) {
      mediaModalVideo.pause();
      mediaModalVideo.removeAttribute("src");
      mediaModalVideo.removeAttribute("poster");
      mediaModalVideo.hidden = true;
      mediaModalVideo.load();
    }
    if (mediaModalImage) {
      mediaModalImage.hidden = true;
      mediaModalImage.removeAttribute("src");
      mediaModalImage.alt = "";
    }
    mediaModalSplit.hidden = false;
    if (mediaModalSplitTop && splitTopSrc) {
      mediaModalSplitTop.alt = alt;
      loadModalImage(mediaModalSplitTop, splitTopSrc);
    }
    mediaModalSplitNav.alt = alt;
    mediaModalSplitMainImage.alt = alt;
    loadModalImage(mediaModalSplitNav, splitNavSrc);
    loadModalImage(mediaModalSplitMainImage, splitMainSrc);
    if (mediaModalSplitMain) mediaModalSplitMain.scrollTop = 0;
  } else if (isPan) {
    hideModalSplit();
    if (mediaModalVideo) {
      mediaModalVideo.pause();
      mediaModalVideo.removeAttribute("src");
      mediaModalVideo.removeAttribute("poster");
      mediaModalVideo.hidden = true;
      mediaModalVideo.load();
    }
    if (mediaModalImage) mediaModalImage.alt = alt;
    setupPanModalMedia(src, trigger);
  } else if (mediaModalImage) {
    hideModalSplit();
    clearPanStageLayout();
    if (mediaModalVideo) {
      mediaModalVideo.pause();
      mediaModalVideo.removeAttribute("src");
      mediaModalVideo.removeAttribute("poster");
      mediaModalVideo.hidden = true;
      mediaModalVideo.load();
    }
    mediaModalImage.hidden = false;
    mediaModalImage.alt = alt;
    mediaModalImage.onerror = () => {
      const fallback = trigger.getAttribute("data-media-fallback");
      if (fallback) {
        mediaModalImage.onerror = null;
        loadModalImage(mediaModalImage, fallback);
      }
    };
    loadModalImage(mediaModalImage, src);
  } else {
    return;
  }

  mediaModal.hidden = false;
  mediaModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("media-modal-open");

  if (isPan) {
    // Always open fully zoomed out — entire artboard in one birds-eye view.
    openPanBirdsEye();
  }

  const closeButton = mediaModal.querySelector(".media-modal-close");
  if (closeButton) closeButton.focus();
}

function closeMediaModal() {
  if (!mediaModal) return;

  mediaModal.hidden = true;
  mediaModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("media-modal-open");

  const mediaDialog = mediaModal.querySelector(".media-modal-dialog");
  if (mediaDialog) {
    mediaDialog.classList.remove("media-modal-dialog--tall");
    mediaDialog.classList.remove("media-modal-dialog--pan");
    mediaDialog.classList.remove("media-modal-dialog--zoom");
    mediaDialog.classList.remove("media-modal-dialog--split");
    mediaDialog.classList.remove("media-modal-dialog--hires");
    mediaDialog.classList.remove("media-modal-dialog--video");
    mediaDialog.scrollTop = 0;
    mediaDialog.scrollLeft = 0;
  }

  showPanZoomControls(false);
  panZoomScale = 1;
  clearPanStageLayout();

  if (mediaModalImage) {
    mediaModalImage.onload = null;
    mediaModalImage.onerror = null;
    mediaModalImage.removeAttribute("src");
    mediaModalImage.alt = "";
    mediaModalImage.hidden = true;
    mediaModalImage.style.width = "";
    mediaModalImage.style.height = "";
    mediaModalImage.style.maxWidth = "";
    mediaModalImage.style.transform = "";
    mediaModalImage.style.transformOrigin = "";
  }

  hideModalSplit();

  if (mediaModalVideo) {
    mediaModalVideo.pause();
    mediaModalVideo.removeAttribute("src");
    mediaModalVideo.removeAttribute("poster");
    mediaModalVideo.removeAttribute("aria-label");
    mediaModalVideo.hidden = true;
    mediaModalVideo.load();
  }

  if (lastMediaTrigger) {
    lastMediaTrigger.focus();
    lastMediaTrigger = null;
  }
}

mediaExpandTriggers.forEach((trigger) => {
  let pointerStart = null;
  let pointerMoved = false;

  trigger.addEventListener("pointerdown", (event) => {
    if (!trigger.hasAttribute("data-media-scroll")) return;
    pointerStart = { x: event.clientX, y: event.clientY };
    pointerMoved = false;
  });

  trigger.addEventListener("pointermove", (event) => {
    if (!pointerStart) return;
    const dx = Math.abs(event.clientX - pointerStart.x);
    const dy = Math.abs(event.clientY - pointerStart.y);
    if (dx > 8 || dy > 8) pointerMoved = true;
  });

  trigger.addEventListener("pointerup", () => {
    // keep pointerMoved until click fires
  });

  trigger.addEventListener("click", (event) => {
    if (trigger.hasAttribute("data-media-scroll") && pointerMoved) {
      event.preventDefault();
      pointerStart = null;
      pointerMoved = false;
      return;
    }
    pointerStart = null;
    pointerMoved = false;
    openMediaModal(trigger);
  });
});

if (mediaModal) {
  mediaModal.querySelectorAll("[data-media-modal-close]").forEach((el) => {
    el.addEventListener("click", closeMediaModal);
  });

  const zoomInBtn = mediaModal.querySelector("[data-media-zoom-in]");
  const zoomOutBtn = mediaModal.querySelector("[data-media-zoom-out]");
  const zoomFitBtn = mediaModal.querySelector("[data-media-zoom-fit]");
  if (zoomInBtn) {
    zoomInBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const dialog = mediaModal.querySelector(".media-modal-dialog");
      if (!dialog?.classList.contains("media-modal-dialog--pan")) return;
      if (panZoomScale <= 1.15) {
        setPanZoom(nearestPanZoomStop(getPanDetailZoom()), getPanViewportCenterAnchor());
      } else {
        stepPanZoom(1, getPanViewportCenterAnchor());
      }
    });
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const dialog = mediaModal.querySelector(".media-modal-dialog");
      if (!dialog?.classList.contains("media-modal-dialog--pan")) return;
      stepPanZoom(-1, getPanViewportCenterAnchor());
    });
  }
  if (zoomFitBtn) {
    zoomFitBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const dialog = mediaModal.querySelector(".media-modal-dialog");
      if (!dialog?.classList.contains("media-modal-dialog--pan")) return;
      fitPanZoom();
    });
  }

  const mediaDialog = mediaModal.querySelector(".media-modal-dialog");
  if (mediaDialog && !panZoomControlsWired) {
    panZoomControlsWired = true;
    let panClickStart = null;

    mediaDialog.addEventListener(
      "wheel",
      (event) => {
        if (!mediaDialog.classList.contains("media-modal-dialog--pan")) return;
        // Pinch-to-zoom (ctrl/meta) or Alt+scroll zooms; plain scroll still pans.
        if (!(event.ctrlKey || event.metaKey || event.altKey)) return;
        event.preventDefault();
        const direction = event.deltaY < 0 ? 1 : -1;
        stepPanZoom(direction, {
          clientX: event.clientX,
          clientY: event.clientY,
        });
      },
      { passive: false }
    );

    // Click-to-zoom: cursor is a zoom tool; click zooms into that point.
    mediaDialog.addEventListener("pointerdown", (event) => {
      if (!mediaDialog.classList.contains("media-modal-dialog--pan")) return;
      if (event.target.closest(".media-modal-close, .media-modal-pan-zoom")) return;
      if (event.button !== 0) return;
      panClickStart = { x: event.clientX, y: event.clientY };
    });

    mediaDialog.addEventListener("click", (event) => {
      if (!mediaDialog.classList.contains("media-modal-dialog--pan")) return;
      if (event.target.closest(".media-modal-close, .media-modal-pan-zoom")) return;
      if (panClickStart) {
        const dx = Math.abs(event.clientX - panClickStart.x);
        const dy = Math.abs(event.clientY - panClickStart.y);
        panClickStart = null;
        // Ignore drags / text selection gestures.
        if (dx > 6 || dy > 6) return;
      }
      const anchor = { clientX: event.clientX, clientY: event.clientY };
      const zoomOut =
        event.altKey ||
        event.metaKey ||
        event.shiftKey ||
        panZoomScale >= getPanZoomMax() - 0.02;
      if (zoomOut) {
        if (panZoomScale <= PAN_ZOOM_MIN + 0.02) return;
        // From deep zoom, one click returns toward Fit in larger steps.
        if (panZoomScale >= getPanDetailZoom() - 0.05) {
          fitPanZoom();
        } else {
          stepPanZoom(-1, anchor);
        }
      } else if (panZoomScale <= 1.15) {
        // From Fit, jump straight to a readable detail level (not +25%).
        setPanZoom(nearestPanZoomStop(getPanDetailZoom()), anchor);
      } else {
        stepPanZoom(1, anchor);
      }
    });

    const syncAltCursor = (event) => {
      const viewport = getPanViewportEl();
      if (!viewport) return;
      const forceOut =
        event.altKey ||
        event.metaKey ||
        event.shiftKey ||
        panZoomScale >= getPanZoomMax() - 0.02;
      viewport.classList.toggle("is-zoom-out-cursor", forceOut);
    };
    window.addEventListener("keydown", syncAltCursor);
    window.addEventListener("keyup", syncAltCursor);

    window.addEventListener("resize", () => {
      if (mediaModal?.hidden) return;
      positionPanZoomControls();
      const dialog = mediaModal.querySelector(".media-modal-dialog");
      if (dialog?.classList.contains("media-modal-dialog--pan")) {
        panFitReady = false;
        reflowPanFit({ resetScale: false });
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !mediaModal.hidden) {
      closeMediaModal();
      return;
    }
    if (mediaModal.hidden) return;
    const dialog = mediaModal.querySelector(".media-modal-dialog");
    if (!dialog?.classList.contains("media-modal-dialog--pan")) return;
    if (event.key === "=" || event.key === "+") {
      event.preventDefault();
      stepPanZoom(1, getPanViewportCenterAnchor());
    } else if (event.key === "-" || event.key === "_") {
      event.preventDefault();
      stepPanZoom(-1, getPanViewportCenterAnchor());
    } else if (event.key === "0") {
      event.preventDefault();
      fitPanZoom();
    } else if (event.key === "1" && !event.metaKey && !event.ctrlKey) {
      event.preventDefault();
      togglePanDetailZoom(getPanViewportCenterAnchor());
    }
  });
}

/* ── Email me: copy address + toast ── */

function copyTextToClipboard(text) {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;left:-9999px;top:0";
    document.body.appendChild(ta);
    ta.select();
    try {
      if (!document.execCommand("copy")) reject(new Error("copy failed"));
      else resolve();
    } catch (err) {
      reject(err);
    } finally {
      ta.remove();
    }
  });
}

function showCopyToast(message) {
  let toast = document.querySelector("[data-copy-toast]");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "copy-toast";
    toast.setAttribute("data-copy-toast", "");
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.remove("is-visible");
  void toast.offsetWidth;
  toast.classList.add("is-visible");
  window.clearTimeout(showCopyToast._timer);
  showCopyToast._timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2200);
}

document.querySelectorAll('.nav-link--accent[href^="mailto:"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const raw = (link.getAttribute("href") || "").replace(/^mailto:/i, "");
    const email = decodeURIComponent(raw.split("?")[0].trim());
    if (!email) {
      window.location.href = link.href;
      return;
    }
    copyTextToClipboard(email)
      .then(() => showCopyToast("Email address copied"))
      .catch(() => {
        window.location.href = link.href;
      });
  });
});
