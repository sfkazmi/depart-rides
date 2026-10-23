(function () {
  try { initCinema(); } catch (err) {
    // Never leave the page half-animated: fall back to the static layout.
    console.error('cinema fallback', err);
    document.documentElement.classList.add('cinema-static');
    document.documentElement.classList.remove('cinema-mobile');
    animateCounters(true);
  }
})();

function initCinema() {
  if (document.body.dataset.page !== 'home') return;

  const cinema = document.getElementById('cinema');
  const pin = document.getElementById('cinema-pin');
  if (!cinema || !pin) return;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hasGsap = typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined';

  if (reduce || !hasGsap) {
    document.documentElement.classList.add('cinema-static');
    animateCounters(true);
    return;
  }

  const small = matchMedia('(max-width: 900px)').matches;
  const gsap = window.gsap;
  gsap.registerPlugin(window.ScrollTrigger);
  window.ScrollTrigger.config({ ignoreMobileResize: true });

  const q = (sel, root = pin) => root.querySelector(sel);
  const chapter = q('#cinema-chapter');
  const progressBar = q('#cinema-progress');
  const film = q('[data-layer="film"]');
  const canvas = q('#cinema-canvas');
  const ctx = canvas.getContext('2d');
  const front = q('[data-layer="front"]');
  const engine = q('[data-layer="engine"]');
  const hero = q('[data-scene="hero"]');
  const cabinScene = q('[data-scene="cabin"]');
  const perfScene = q('[data-scene="perf"]');
  const panels = gsap.utils.toArray('[data-panel]', pin);

  // ---- frame sequence (scrubbed like a video; reliable on iOS Safari) ----
  const COUNT = 100;
  const dir = small ? 'assets/seq/m/' : 'assets/seq/d/';
  const frames = new Array(COUNT);
  let current = -1;
  const playhead = { f: 0 };

  function sizeCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, small ? 2 : 1.5);
    canvas.width = Math.round(canvas.clientWidth * dpr);
    canvas.height = Math.round(canvas.clientHeight * dpr);
    current = -1;
    draw();
  }
  function nearestLoaded(i) {
    for (let d = 0; d < COUNT; d++) {
      if (frames[i - d] && frames[i - d].complete && frames[i - d].naturalWidth) return frames[i - d];
      if (frames[i + d] && frames[i + d].complete && frames[i + d].naturalWidth) return frames[i + d];
    }
    return null;
  }
  function draw() {
    const i = Math.max(0, Math.min(COUNT - 1, Math.round(playhead.f)));
    const img = nearestLoaded(i);
    if (!img || (i === current && img === frames[i])) return;
    current = img === frames[i] ? i : -1;
    const cw = canvas.width, ch = canvas.height;
    const s = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
    const w = img.naturalWidth * s, h = img.naturalHeight * s;
    // keep the car/door (right of centre) in view on portrait screens
    const fx = small ? 0.62 : 0.5;
    ctx.drawImage(img, (cw - w) * fx, (ch - h) / 2, w, h);
  }
  function load(i) {
    if (frames[i]) return;
    const im = new Image();
    im.decoding = 'async';
    im.onload = draw;
    im.src = dir + String(i + 1).padStart(3, '0') + '.webp';
    frames[i] = im;
  }
  load(0);
  // load key frames first, then fill in
  for (let step = 16; step >= 1; step = step >> 1) for (let i = 0; i < COUNT; i += step) load(i);
  window.addEventListener('resize', sizeCanvas);
  sizeCanvas();

  // On phones the price/perf block is too tall for a pinned screen: show it as a normal section after the film.
  if (small) {
    document.documentElement.classList.add('cinema-mobile');
    cinema.after(perfScene);
    gsap.set([front, engine], { display: 'none' });
  }

  gsap.set([cabinScene, front, engine].concat(small ? [] : [perfScene]), { autoAlpha: 0 });
  gsap.set(panels, { autoAlpha: 0, y: 28 });
  gsap.set(film, { autoAlpha: 0 });

  gsap.timeline({ defaults: { ease: 'power3.out' } })
    .to(film, { autoAlpha: 1, duration: 1.2 }, 0)
    .from(hero.querySelectorAll('.line span, .eyebrow, .intro, .hero-actions, .scroll-hint'), {
      y: 36, autoAlpha: 0, duration: 1.05, stagger: 0.08
    }, 0.3);

  const chapters = small
    ? [{ at: 0, text: '01  ·  ARRIVAL' }, { at: 0.45, text: '02  ·  THE CABIN' }]
    : [{ at: 0, text: '01  ·  ARRIVAL' }, { at: 0.3, text: '02  ·  THE CABIN' }, { at: 0.62, text: '03  ·  THE MACHINE' }];

  let countersFired = false;
  function setChapter(progress) {
    let text = chapters[0].text;
    for (const c of chapters) if (progress >= c.at) text = c.text;
    if (chapter && chapter.textContent !== text) chapter.textContent = text;
    if (progressBar) progressBar.style.transform = `scaleX(${progress})`;
  }

  const filmEnd = small ? 0.78 : 0.56; // fraction of the pinned scroll that plays the film
  const tl = gsap.timeline({
    defaults: { ease: 'none' },
    scrollTrigger: {
      trigger: pin,
      start: 'top top',
      end: small ? '+=300%' : '+=420%',
      pin: true,
      scrub: small ? true : 0.5,
      anticipatePin: 1,
      invalidateOnRefresh: true,
      onUpdate(self) {
        setChapter(self.progress);
        if (!small && self.progress > 0.7 && !countersFired) { countersFired = true; animateCounters(false); }
      }
    }
  });

  tl.to(playhead, { f: COUNT - 1, duration: filmEnd, onUpdate: draw }, 0)
    .to(hero, { autoAlpha: 0, y: -24, duration: 0.08 }, 0.1);

  if (small) {
    tl.to(cabinScene, { autoAlpha: 1, duration: 0.08 }, 0.6)
      .to(panels, { autoAlpha: 1, y: 0, stagger: 0.03, duration: 0.08 }, 0.64)
      .to({}, { duration: 0.1 }, 0.9);
    window.ScrollTrigger.create({ trigger: perfScene, start: 'top 75%', once: true, onEnter: () => animateCounters(false) });
  } else {
    tl.to(cabinScene, { autoAlpha: 1, duration: 0.06 }, 0.4)
      .to(panels, { autoAlpha: 1, y: 0, stagger: 0.02, duration: 0.06 }, 0.42)
      .to(cabinScene, { autoAlpha: 0, duration: 0.06 }, 0.58)
      .to(film, { autoAlpha: 0, duration: 0.1 }, 0.6)
      .to(front, { autoAlpha: 1, scale: 1.08, duration: 0.14 }, 0.62)
      .to(front, { scale: 1.22, duration: 0.1 }, 0.74)
      .to(engine, { autoAlpha: 0.72, duration: 0.1 }, 0.78)
      .to(perfScene, { autoAlpha: 1, duration: 0.08 }, 0.76)
      .to([front, engine], { scale: 1.06, duration: 0.1 }, 0.9);
  }

  window.addEventListener('load', () => window.ScrollTrigger.refresh());
}

function animateCounters(instant) {
  const nodes = document.querySelectorAll('[data-count]');
  nodes.forEach((el) => {
    const target = Number(el.dataset.count || 0);
    if (!target) return;
    if (instant || typeof window.gsap === 'undefined') {
      el.textContent = String(target).padStart(2, '0');
      return;
    }
    const proxy = { val: 0 };
    window.gsap.to(proxy, {
      val: target,
      duration: 1.4,
      ease: 'power2.out',
      onUpdate() {
        el.textContent = String(Math.round(proxy.val)).padStart(2, '0');
      }
    });
  });
}
