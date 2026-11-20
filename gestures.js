/* Gesture mode — camera + hand-gesture navigation (homepage prototype).
   Hand tracking runs fully on-device via MediaPipe HandLandmarker.
   - Point (index finger): move the virtual cursor
   - Thumbs up (hold briefly): click
   - Open palm: scroll down · Closed fist: scroll up
   - Thumb out to the side (hold, either hand): go back (all pages except home)
   Mouse / touch / keyboard keep working at all times. */

const toggles = [...document.querySelectorAll("[data-gesture-toggle]")];
const isHome = document.body.classList.contains("page-home");
const SESSION_KEY = "gesture-mode-on";
function rememberOn(on) {
  try { on ? sessionStorage.setItem(SESSION_KEY, "1") : sessionStorage.removeItem(SESSION_KEY); } catch { /* private mode */ }
}

function setToggles(on) {
  toggles.forEach((btn) => {
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    const label = btn.querySelector("[data-gesture-toggle-label]") || btn;
    label.textContent = on
      ? btn.dataset.labelOn || "✋ Stop gesture mode"
      : btn.dataset.labelOff || "✋ Gesture mode";
  });
}
const panel = document.querySelector("[data-gesture-panel]");
const liveWrap = document.querySelector("[data-gesture-live]");
const closeBtn = document.querySelector("[data-gesture-close]");
const video = document.querySelector("[data-gesture-video]");
const statusEl = document.querySelector("[data-gesture-status]");
const cursorEl = document.querySelector("[data-gesture-cursor]");
const cursorLabel = document.querySelector("[data-gesture-cursor-label]");

let active = false;
let stream = null;
let landmarker = null;
let rafId = null;
let lastVideoTime = -1;
let cursor = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
let thumbFrames = 0;
let backFrames = 0;
let backFired = false;
let fistFrames = 0;
let lastFrameAt = 0;
const SCROLL_SPEED = 650; // px per second
let clickArmed = true;
let lastClickAt = 0;

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
}

function showNotice(msg) {
  if (!panel || !statusEl) return;
  panel.hidden = false;
  if (liveWrap) liveWrap.hidden = false;
  if (video) video.hidden = true;
  setStatus(msg);
  clearTimeout(showNotice.t);
  showNotice.t = setTimeout(() => {
    if (!active) { panel.hidden = true; if (video) video.hidden = false; }
  }, 5000);
}

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function isExtended(lm, tip, pip) {
  const wrist = lm[0];
  return dist(lm[tip], wrist) > dist(lm[pip], wrist) * 1.12;
}

async function createLandmarker(mp) {
  const vision = await mp.FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
  );
  const options = (delegate) => ({
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
      delegate,
    },
    runningMode: "VIDEO",
    numHands: 1,
  });
  try {
    return await mp.HandLandmarker.createFromOptions(vision, options("GPU"));
  } catch {
    return await mp.HandLandmarker.createFromOptions(vision, options("CPU"));
  }
}

async function startGestures() {
  if (active) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("Camera isn’t supported in this browser.");
    return;
  }
  active = true;
  rememberOn(true);
  setToggles(true);
  if (video) video.hidden = false;
  panel.hidden = false;
  if (liveWrap) liveWrap.hidden = false;
  cursorEl.hidden = false;
  setStatus("Requesting camera…");

  try {
    const s = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    if (!active) { s.getTracks().forEach((t) => t.stop()); return; } // turned off while the prompt was open
    stream = s;
    video.srcObject = stream;
    await video.play();
  } catch {
    stopGestures();
    showNotice("Camera permission denied. Mouse and keyboard still work.");
    return;
  }

  try {
    setStatus("Loading hand tracking…");
    const mp = await import(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs"
    );
    const lmk = await createLandmarker(mp);
    if (!active) { try { lmk.close(); } catch {} return; }
    landmarker = lmk;
  } catch {
    stopGestures();
    showNotice("Couldn’t load hand tracking. Check your connection and try again.");
    return;
  }

  if (!active) return;
  setStatus("Show your hand to the camera.");
  loop();
}

function stopGestures(opts = {}) {
  if (!opts.keepSession) rememberOn(false);
  active = false;
  setToggles(false);
  if (liveWrap) liveWrap.hidden = true;
  panel.hidden = true;
  cursorEl.hidden = true;
  fistFrames = 0;
  lastFrameAt = 0;
  thumbFrames = 0;
  clickArmed = true;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  video.srcObject = null;
  if (landmarker) {
    try { landmarker.close(); } catch { /* already closed */ }
    landmarker = null;
  }
  lastVideoTime = -1;
}

function goBack() {
  const sameSiteReferrer = document.referrer && new URL(document.referrer).origin === location.origin;
  if (history.length > 1 && sameSiteReferrer) history.back();
  else location.href = "./index.html";
}

function fireClick(x, y) {
  const el = document.elementFromPoint(x, y);
  if (!el) return;
  const target = el.closest("a, button, summary, [role='button'], input, label") || el;
  target.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: x, clientY: y }));
  target.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: x, clientY: y }));
  if (typeof target.click === "function") target.click();
}

function loop() {
  if (!active) return;
  rafId = requestAnimationFrame(loop);
  if (!landmarker || video.readyState < 2) return;

  let results = null;
  if (video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    try {
      results = landmarker.detectForVideo(video, performance.now());
    } catch {
      return;
    }
  } else {
    return;
  }

  const lm = results?.landmarks?.[0];
  if (!lm) {
    cursorLabel.textContent = "Show your hand";
    fistFrames = 0;
  lastFrameAt = 0;
    return;
  }

  const indexExt = isExtended(lm, 8, 6);
  const middleExt = isExtended(lm, 12, 10);
  const ringExt = isExtended(lm, 16, 14);
  const pinkyExt = isExtended(lm, 20, 18);
  const openPalm = indexExt && middleExt && ringExt && pinkyExt;
  const fingersCurled = !indexExt && !middleExt && !ringExt && !pinkyExt;

  // Thumbs up (strict, so a fist never reads as a click):
  // other fingers curled, thumb pointing up, tip clearly above the knuckles
  // and well away from the curled fingers (in a fist the thumb rests on them).
  const handSize = dist(lm[0], lm[9]) || 0.1;
  const thumbVertical =
    lm[4].y < lm[3].y && lm[3].y < lm[2].y &&
    Math.abs(lm[4].y - lm[2].y) > Math.abs(lm[4].x - lm[2].x) * 1.2;
  const tipAboveKnuckles = lm[5].y - lm[4].y > handSize * 0.35;
  const tipAwayFromFingers =
    Math.min(dist(lm[4], lm[6]), dist(lm[4], lm[10])) > handSize * 0.5;
  const thumbsUp = fingersCurled && thumbVertical && tipAboveKnuckles && tipAwayFromFingers;

  // Thumb out (either hand): thumb sideways, on the far side of the index knuckle
  // from the pinky. Works for left and right hands because it's relative to the hand.
  const outward = Math.sign(lm[5].x - lm[17].x) || 1;
  const thumbSideways = Math.abs(lm[4].x - lm[2].x) > Math.abs(lm[4].y - lm[2].y) * 1.3;
  const tipOutSide = (lm[4].x - lm[5].x) * outward > handSize * 0.3;
  const thumbLeft = !isHome && fingersCurled && thumbSideways && tipOutSide && tipAwayFromFingers;

  // Only the pointing index finger (or an open palm, for scrolling) moves the cursor.
  // Thumbs up freezes it, so changing hand shape doesn't knock it off target.
  if (indexExt) {
    const targetX = (1 - lm[8].x) * window.innerWidth; // mirror the selfie view
    const targetY = lm[8].y * window.innerHeight;
    cursor.x += (targetX - cursor.x) * 0.35;
    cursor.y += (targetY - cursor.y) * 0.35;
    cursorEl.style.transform = `translate(${cursor.x}px, ${cursor.y}px) translate(-50%, -50%)`;
  }

  // Steady scrolling: open palm scrolls down, closed fist scrolls up.
  const now = performance.now();
  const dt = Math.min(64, now - (lastFrameAt || now));
  lastFrameAt = now;
  const fist = fingersCurled && !thumbsUp && !thumbLeft;
  fistFrames = fist ? fistFrames + 1 : 0;
  if (openPalm || fistFrames >= 8) {
    const dir = openPalm ? 1 : -1;
    cursorEl.classList.remove("gesture-cursor--pinch");
    cursorLabel.textContent = dir > 0 ? "Scroll ↓" : "Scroll ↑";
    window.scrollBy(0, dir * SCROLL_SPEED * (dt / 1000));
    thumbFrames = 0;
    clickArmed = true;
    return;
  }

  if (thumbLeft) {
    backFrames += 1;
    thumbFrames = 0;
    cursorEl.classList.add("gesture-cursor--pinch");
    if (backFrames >= 14 && !backFired) {
      backFired = true;
      cursorLabel.textContent = "Back";
      goBack();
    } else if (!backFired) {
      cursorLabel.textContent = "Hold 👍 sideways to go back";
    }
    return;
  }
  backFrames = 0;
  backFired = false;

  if (thumbsUp) {
    thumbFrames += 1;
    cursorEl.classList.add("gesture-cursor--pinch");
    // Hold for ~10 frames (about 0.3s) before clicking; one click per thumbs up.
    if (thumbFrames >= 10 && clickArmed) {
      const now = performance.now();
      if (now - lastClickAt > 700) {
        lastClickAt = now;
        clickArmed = false;
        cursorLabel.textContent = "Click!";
        fireClick(cursor.x, cursor.y);
      }
    } else if (clickArmed) {
      cursorLabel.textContent = "Hold 👍";
    }
    return;
  }

  thumbFrames = 0;
  clickArmed = true;
  cursorEl.classList.remove("gesture-cursor--pinch");
  cursorLabel.textContent = indexExt ? "Point" : "👍 to click";
}

/* Legend stays open unless the user closes it (remembered across visits) */
let legendClosed = false;
try {
  legendClosed = localStorage.getItem("gesture-legend-closed") === "1";
} catch { /* private mode */ }
if (panel && legendClosed) panel.hidden = true;

if (closeBtn) {
  closeBtn.addEventListener("click", () => {
    legendClosed = true;
    try {
      localStorage.setItem("gesture-legend-closed", "1");
    } catch { /* private mode */ }
    if (active) stopGestures();
    panel.hidden = true;
  });
}

if (toggles.length) {
  toggles.forEach((btn) =>
    btn.addEventListener("click", () => {
      if (active) stopGestures();
      else startGestures();
    })
  );
  window.addEventListener("pagehide", () => stopGestures({ keepSession: true }));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && active) stopGestures();
  });
}

/* Keep gesture mode on across pages in this tab (desktop only). */
try {
  const desktop = matchMedia("(hover: hover) and (pointer: fine) and (min-width: 821px)").matches;
  if (toggles.length && desktop && sessionStorage.getItem(SESSION_KEY) === "1") startGestures();
} catch { /* ignore */ }
