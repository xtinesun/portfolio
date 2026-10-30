/* Gesture mode — camera + hand-gesture navigation (homepage prototype).
   Hand tracking runs fully on-device via MediaPipe HandLandmarker.
   - Point (index finger): move the virtual cursor
   - Pinch (thumb + index): click
   - Open palm, move up/down: scroll
   Mouse / touch / keyboard keep working at all times. */

const toggleBtn = document.querySelector("[data-gesture-toggle]");
const panel = document.querySelector("[data-gesture-panel]");
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
let pinchDown = false;
let lastClickAt = 0;
let palmPrevY = null;

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
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
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("Camera isn’t supported in this browser.");
    return;
  }
  active = true;
  toggleBtn.setAttribute("aria-pressed", "true");
  toggleBtn.textContent = "✋ Stop gesture mode";
  panel.hidden = false;
  cursorEl.hidden = false;
  setStatus("Requesting camera…");

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
  } catch {
    setStatus("Camera permission denied — mouse and keyboard still work.");
    stopGestures();
    return;
  }

  try {
    setStatus("Loading hand tracking…");
    const mp = await import(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/dist/vision_bundle.mjs"
    );
    landmarker = await createLandmarker(mp);
  } catch {
    setStatus("Couldn’t load hand tracking (check connection).");
    stopGestures();
    return;
  }

  if (!active) return;
  setStatus("Show your hand to the camera.");
  loop();
}

function stopGestures() {
  active = false;
  toggleBtn.setAttribute("aria-pressed", "false");
  toggleBtn.textContent = "✋ Gesture mode";
  panel.hidden = true;
  cursorEl.hidden = true;
  palmPrevY = null;
  pinchDown = false;
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
    palmPrevY = null;
    return;
  }

  const indexExt = isExtended(lm, 8, 6);
  const middleExt = isExtended(lm, 12, 10);
  const ringExt = isExtended(lm, 16, 14);
  const pinkyExt = isExtended(lm, 20, 18);
  const openPalm = indexExt && middleExt && ringExt && pinkyExt;
  const pinchDist = dist(lm[4], lm[8]);

  // Pointer position: pinch midpoint while pinching, otherwise index fingertip.
  const anchor = pinchDist < 0.09
    ? { x: (lm[4].x + lm[8].x) / 2, y: (lm[4].y + lm[8].y) / 2 }
    : lm[8];
  const targetX = (1 - anchor.x) * window.innerWidth; // mirror the selfie view
  const targetY = anchor.y * window.innerHeight;
  cursor.x += (targetX - cursor.x) * 0.35;
  cursor.y += (targetY - cursor.y) * 0.35;
  cursorEl.style.transform = `translate(${cursor.x}px, ${cursor.y}px) translate(-50%, -50%)`;

  if (openPalm && pinchDist >= 0.05) {
    // Grab-and-drag scroll: page follows the palm.
    cursorEl.classList.remove("gesture-cursor--pinch");
    cursorLabel.textContent = "Scroll";
    if (palmPrevY !== null) {
      window.scrollBy(0, -(cursor.y - palmPrevY) * 2.2);
    }
    palmPrevY = cursor.y;
    pinchDown = false;
    return;
  }
  palmPrevY = null;

  const pinching = pinchDist < 0.05;
  cursorEl.classList.toggle("gesture-cursor--pinch", pinching);
  if (pinching) {
    cursorLabel.textContent = "Click!";
    const now = performance.now();
    if (!pinchDown && now - lastClickAt > 700) {
      lastClickAt = now;
      fireClick(cursor.x, cursor.y);
    }
    pinchDown = true;
  } else {
    cursorLabel.textContent = indexExt && !middleExt ? "Point" : "Pinch to click";
    pinchDown = false;
  }
}

if (toggleBtn) {
  toggleBtn.addEventListener("click", () => {
    if (active) stopGestures();
    else startGestures();
  });
  window.addEventListener("beforeunload", stopGestures);
}
