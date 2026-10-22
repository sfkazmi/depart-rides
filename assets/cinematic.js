(function () {
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

  const gsap = window.gsap;
  gsap.registerPlugin(window.ScrollTrigger);

  const q = (sel, root = pin) => root.querySelector(sel);
  const chapter = q('#cinema-chapter');
  const progressBar = q('#cinema-progress');
  const side = q('[data-layer="side"]');
  const interior = q('[data-layer="interior"]');
  const cabin = q('[data-layer="cabin"]');
  const front = q('[data-layer="front"]');
  const engine = q('[data-layer="engine"]');
  const hero = q('[data-scene="hero"]');
  const cabinScene = q('[data-scene="cabin"]');
  const perfScene = q('[data-scene="perf"]');
  const panels = gsap.utils.toArray('[data-panel]', pin);
  const mm = gsap.matchMedia();

  gsap.set([interior, cabin, front, engine, cabinScene, perfScene], { autoAlpha: 0 });
  gsap.set(panels, { autoAlpha: 0, y: 28 });
  gsap.set(side, { xPercent: 42, autoAlpha: 0 });

  const intro = gsap.timeline({ defaults: { ease: 'power3.out' } });
  intro
    .to(side, { xPercent: 0, autoAlpha: 1, duration: 1.85, delay: 0.12 }, 0)
    .from(hero.querySelectorAll('.line span, .eyebrow, .intro, .hero-actions, .scroll-hint'), {
      y: 36,
      autoAlpha: 0,
      duration: 1.05,
      stagger: 0.08,
      ease: 'power3.out'
    }, 0.32);

  const chapters = [
    { at: 0, text: '01  ·  ARRIVAL' },
    { at: 0.28, text: '02  ·  THE CABIN' },
    { at: 0.68, text: '03  ·  THE MACHINE' }
  ];

  let countersFired = false;

  function setChapter(progress) {
    let text = chapters[0].text;
    for (const c of chapters) if (progress >= c.at) text = c.text;
    if (chapter && chapter.textContent !== text) chapter.textContent = text;
    if (progressBar) progressBar.style.transform = `scaleX(${progress})`;
  }

  function buildTimeline(scaleMax, origin) {
    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      scrollTrigger: {
        trigger: pin,
        start: 'top top',
        end: '+=420%',
        pin: true,
        scrub: 0.65,
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate(self) {
          setChapter(self.progress);
          if (self.progress > 0.78 && !countersFired) {
            countersFired = true;
            animateCounters(false);
          }
        }
      }
    });

    tl.to(hero, { autoAlpha: 0, y: -30, duration: 0.12 }, 0.16)
      .to(side, {
        scale: scaleMax,
        xPercent: -6,
        transformOrigin: origin,
        duration: 0.28
      }, 0.12)
      .to(interior, { autoAlpha: 1, scale: 1.08, duration: 0.16 }, 0.26)
      .to(side, { autoAlpha: 0, duration: 0.12 }, 0.3)
      .to(cabinScene, { autoAlpha: 1, duration: 0.1 }, 0.32)
      .to(panels, { autoAlpha: 1, y: 0, stagger: 0.04, duration: 0.12 }, 0.34)
      .to(cabin, { autoAlpha: 0.55, duration: 0.12 }, 0.46)
      .to(interior, { autoAlpha: 0.35, duration: 0.12 }, 0.5)
      .to(cabinScene, { autoAlpha: 0, duration: 0.1 }, 0.62)
      .to([interior, cabin], { autoAlpha: 0, duration: 0.1 }, 0.64)
      .to(front, { autoAlpha: 1, scale: 1.12, duration: 0.16 }, 0.66)
      .to(front, { scale: 1.28, duration: 0.12 }, 0.78)
      .to(engine, { autoAlpha: 0.92, duration: 0.12 }, 0.8)
      .to(perfScene, { autoAlpha: 1, duration: 0.1 }, 0.78)
      .to([front, engine], { scale: 1.05, duration: 0.12 }, 0.9);

    return tl;
  }

  mm.add('(min-width: 901px)', () => buildTimeline(2.55, '58% 42%'));
  mm.add('(max-width: 900px)', () => buildTimeline(1.85, '50% 48%'));

  window.addEventListener('load', () => window.ScrollTrigger.refresh());
})();

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
