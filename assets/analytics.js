/* Google Analytics 4 for Depart Rides.
 * Put your GA4 Measurement ID (e.g. 'G-XXXXXXXXXX') below. While it is empty,
 * nothing is loaded and no data is sent. */
const GA_ID = '';

(function () {
  if (!GA_ID) return;
  const s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA_ID);
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { dataLayer.push(arguments); };
  gtag('js', new Date());
  gtag('config', GA_ID);

  const page = location.pathname.split('/').pop().replace('.html', '') || 'index';
  const carName = () => {
    const h = document.querySelector('.panel h2');
    return page === 'vehicle' && h ? h.textContent.trim() : '';
  };
  const carFromWa = (href) => {
    try { const t = new URL(href).searchParams.get('text') || ''; const m = t.match(/book (?:the )?(.+?)(?: for|[.,]|$)/i); return m ? m[1] : ''; } catch (e) { return ''; }
  };

  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (/wa\.me|whatsapp/i.test(href)) {
      gtag('event', 'whatsapp_click', { car_name: carName() || carFromWa(a.href) || 'general', page, link_text: a.textContent.trim().slice(0, 60) });
    } else if (href.startsWith('tel:')) {
      gtag('event', 'call_click', { car_name: carName() || 'general', page });
    }
  }, true);

  if (page === 'vehicle') {
    window.addEventListener('DOMContentLoaded', () => {
      gtag('event', 'vehicle_view', { car_id: new URLSearchParams(location.search).get('id') || '', car_name: carName() });
    });
  }
})();
