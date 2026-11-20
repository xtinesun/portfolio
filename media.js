/* Case-study video helpers
   - Inline loops play only while on screen, and never auto-play with reduced motion.
   - Every inline loop gets a pause / play control (WCAG 2.2.2).
   - Chaptered players advance through chapters and let viewers jump between them. */
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const videos = [...document.querySelectorAll("video.case-media-video, video.case-media-img--hero")];
  const userPaused = new WeakSet();
  const play = (v) => { const p = v.play(); if (p) p.catch(() => {}); };

  videos.forEach((v) => {
    v.removeAttribute("autoplay");
    v.autoplay = false;
    v.pause();
    const host = v.closest("figure") || v.parentElement;
    if (!host) return;
    host.classList.add("has-video-control");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "video-control";
    const sync = () => {
      const paused = v.paused;
      btn.setAttribute("aria-label", paused ? "Play video" : "Pause video");
      btn.dataset.state = paused ? "paused" : "playing";
    };
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (v.paused) { userPaused.delete(v); play(v); }
      else { userPaused.add(v); v.pause(); }
    });
    v.addEventListener("play", sync);
    v.addEventListener("pause", sync);
    sync();
    host.appendChild(btn);

    if (reduce) return;
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting && !userPaused.has(v)) play(v);
          else if (!en.isIntersecting) v.pause();
        });
      }, { threshold: 0.35 }).observe(v);
    } else {
      play(v);
    }
  });

  document.querySelectorAll("[data-chapters]").forEach((wrap) => {
    const v = wrap.querySelector("video");
    const tabs = [...wrap.querySelectorAll("[data-chapter]")];
    if (!v || !tabs.length) return;
    let current = 0;
    const load = (i, autoplay) => {
      current = (i + tabs.length) % tabs.length;
      const t = tabs[current];
      tabs.forEach((b, j) => b.setAttribute("aria-pressed", j === current ? "true" : "false"));
      v.poster = t.dataset.poster;
      v.innerHTML =
        `<source src="${t.dataset.webm}" type="video/webm" />` +
        `<source src="${t.dataset.mp4}" type="video/mp4" />`;
      v.load();
      if (autoplay) play(v);
    };
    tabs.forEach((t, i) =>
      t.addEventListener("click", () => { userPaused.delete(v); load(i, true); })
    );
    v.addEventListener("ended", () => load(current + 1, !reduce));
  });
})();

/* Open a collapsed "Go deeper" section when a link points inside it */
(() => {
  const openFor = (hash) => {
    if (!hash || hash.length < 2) return;
    let el;
    try { el = document.querySelector(hash); } catch { return; }
    const d = el && el.closest("details");
    if (d && !d.open) d.open = true;
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (a) openFor(a.getAttribute("href"));
  });
  openFor(location.hash);
})();
