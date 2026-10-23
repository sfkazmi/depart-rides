(function () {
  if (document.body.dataset.page !== 'home') return;

  const cinema = document.getElementById('cinema');
  const pin = document.getElementById('cinema-pin');
  if (!cinema || !pin) return;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hasGsap = typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined';

  // Small screens get the static, fully scrollable layout (no pinned door sequence).
  const small = matchMedia('(max-width: 900px)').matches;

  if (reduce || !hasGsap || small) {
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
  const door = q('[data-layer="door"]');
  const through = q('[data-layer="through"]');
  const dash = q('[data-layer="dash"]');
  const dashImg = dash.querySelector('img');
  const front = q('[data-layer="front"]');
  const engine = q('[data-layer="engine"]');
  const hero = q('[data-scene="hero"]');
  const cabinScene = q('[data-scene="cabin"]');
  const perfScene = q('[data-scene="perf"]');
  const panels = gsap.utils.toArray('[data-panel]', pin);
  const mm = gsap.matchMedia();

  gsap.set([door, through, dash, front, engine, cabinScene, perfScene], { autoAlpha: 0 });
  gsap.set(panels, { autoAlpha: 0, y: 28 });
  gsap.set(side, { xPercent: 42, autoAlpha: 0 });
  gsap.set(dashImg, { xPercent: 10, rotateY: 14, scale: 1.06, transformPerspective: 1400 });

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
    { at: 0.3, text: '02  ·  THE CABIN' },
    { at: 0.6, text: '03  ·  THE MACHINE' }
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
          if (self.progress > 0.7 && !countersFired) {
            countersFired = true;
            animateCounters(false);
          }
        }
      }
    });

    // 1. door opens  2. camera moves in through the door  3. pan across the dashboard
    tl.to(hero, { autoAlpha: 0, y: -24, duration: 0.1 }, 0.1)
      .to(door, { autoAlpha: 1, duration: 0.12 }, 0.08)
      .to([side, door], { scale: scaleMax, transformOrigin: origin, duration: 0.18 }, 0.16)
      .fromTo(through, { autoAlpha: 0, scale: 1.25 }, { autoAlpha: 1, scale: 1.04, duration: 0.12 }, 0.26)
      .to([side, door], { autoAlpha: 0, duration: 0.06 }, 0.32)
      .to(through, { scale: 1.45, xPercent: -6, duration: 0.1 }, 0.36)
      .to(dash, { autoAlpha: 1, duration: 0.08 }, 0.4)
      .to(through, { autoAlpha: 0, duration: 0.06 }, 0.44)
      .to(dashImg, { xPercent: -10, rotateY: -10, scale: 1, duration: 0.2 }, 0.4)
      .to(cabinScene, { autoAlpha: 1, duration: 0.06 }, 0.5)
      .to(panels, { autoAlpha: 1, y: 0, stagger: 0.02, duration: 0.06 }, 0.51)
      .to(cabinScene, { autoAlpha: 0, duration: 0.06 }, 0.6)
      .to(dash, { autoAlpha: 0, duration: 0.1 }, 0.62)
      .to(front, { autoAlpha: 1, scale: 1.08, duration: 0.14 }, 0.62)
      .to(front, { scale: 1.22, duration: 0.1 }, 0.74)
      .to(engine, { autoAlpha: 0.72, duration: 0.1 }, 0.78)
      .to(perfScene, { autoAlpha: 1, duration: 0.08 }, 0.76)
      .to([front, engine], { scale: 1.06, duration: 0.1 }, 0.9);

    return tl;
  }

  mm.add('(min-width: 901px)', () => buildTimeline(2.55, '58% 42%'));

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
