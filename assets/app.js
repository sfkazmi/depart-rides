const PHONE_DISPLAY = '0339 9999038';
const PHONE_TEL = 'tel:+923399999038';
const wa = (text = "Hi Depart Rides, I'd like to book a car.") => `https://wa.me/923399999038?text=${encodeURIComponent(text)}`;
const bookText = (name) => `Hi Depart Rides, I'd like to book the ${name}.`;
const WA_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6a2.7 2.7 0 0 0 1.7-1.2 2.2 2.2 0 0 0 .2-1.2c-.1-.1-.3-.2-.5-.3z"/></svg>';
const PHOTO_CREDITS = {
  'haval-h6': [['Haval H6 III 007', 'File:Haval_H6_III_007.jpg', 'Jengtingchen', 'CC BY-SA 4.0']],
  'corolla-xli': [['Toyota Altis 2.0 V (Attitude Black)', 'File:Toyota_Altis_2.0_V_(Attitude_Black).jpg', 'Captainmorlypogi1959', 'CC BY-SA 4.0']]
};
const creditHtml = (id) => (PHOTO_CREDITS[id] || []).map(([t, f, a, l]) => `<a href="https://commons.wikimedia.org/wiki/${encodeURI(f)}" target="_blank" rel="noopener">${t}</a> by ${a}, ${l}${l === 'CC0' ? '' : ' (cropped)'}`).join('; ');
const CARS = [
  {
    id: 'prado',
    name: 'Toyota Prado',
    tag: '2024 · Premium SUV',
    type: 'SUV',
    year: '2024',
    seats: '7 seats',
    rate: 'On request',
    rates: [
      { label: 'Local Jhelum', range: 'Rs 15,000 – 18,000', note: 'With fuel' },
      { label: 'Outside city', range: 'Rs 14,000 – 17,000', note: 'Without fuel' },
      { label: 'Islamabad & Islamabad Airport', range: 'Rs 27,000 – 30,000', note: 'With fuel' }
    ],
    image: 'assets/prado-three-quarter.jpg',
    gallery: ['assets/prado-three-quarter.jpg', 'assets/prado-front.jpg', 'assets/prado-angle.jpg'],
    desc: 'A commanding premium SUV for refined city travel, family journeys and comfortable long-distance adventures.'
  },
  {
    id: 'haval-h6',
    name: 'Haval H6',
    tag: '2025 · Modern comfort',
    type: 'SUV',
    year: '2025',
    seats: '5 seats',
    rate: 'On request',
    rates: [
      { label: 'Local Jhelum', range: 'Rs 12,000 – 15,000', note: 'With fuel' },
      { label: 'Outside city', range: 'Rs 10,000 – 12,000', note: 'Without fuel' }
    ],
    image: 'assets/haval-h6-front.jpg',
    gallery: ['assets/haval-h6-front.jpg', 'assets/haval-h6-rear.jpg'],
    desc: 'A contemporary SUV with a spacious cabin, striking presence and comfort for everyday and special trips.'
  },
  {
    id: 'jetour-t2',
    name: 'Jetour T2',
    tag: '2026 · White',
    type: 'SUV',
    year: '2026',
    seats: '5 seats',
    rate: 'Price on demand',
    image: 'assets/jetour-t2-front.jpg',
    gallery: ['assets/jetour-t2-front.jpg', 'assets/jetour-t2-rear.jpg', 'assets/jetour-t2-side.jpg'],
    desc: 'A white 2026 Jetour T2 with bold, adventure-inspired design with the versatility to make every journey memorable.'
  },
  {
    id: 'corolla-xli',
    name: 'Toyota Corolla XLi',
    tag: '2014 · Black',
    type: 'Sedan',
    year: '2014',
    seats: '5 seats',
    specs: ['1.3L petrol', 'Manual'],
    rate: 'Price on demand',
    image: 'assets/corolla-xli-front.jpg',
    desc: 'A dependable, economical black 2014 Corolla XLi sedan with a 1.3L petrol engine and manual gearbox — ideal for city travel, airport transfers and everyday plans.'
  },
  {
    id: 'land-cruiser-v8',
    name: 'Toyota Land Cruiser V8',
    tag: '2018 · Actual vehicle',
    type: 'Luxury',
    year: '2018',
    seats: 'Capacity on request',
    rate: 'On request',
    rates: [
      { label: 'Local Jhelum', range: 'Rs 20,000 – 25,000', note: 'With fuel' },
      { label: 'Outside city', range: 'Rs 18,000 – 22,000', note: 'Without fuel' },
      { label: 'Islamabad & Islamabad Airport', range: 'Rs 35,000 – 40,000', note: 'With fuel' }
    ],
    image: 'assets/land-cruiser-side.jpg',
    gallery: [
      'assets/land-cruiser-side.jpg',
      'assets/land-cruiser-side-2.jpg',
      'assets/v8-side.jpg',
      'assets/v8-side-alt.jpg',
      'assets/land-cruiser-front.jpg',
      'assets/v8-front.jpg',
      'assets/land-cruiser-rear.jpg',
      'assets/v8-rear.jpg'
    ],
    desc: 'Our flagship white Land Cruiser V8 delivers a commanding presence and an elevated experience for executive journeys and special occasions.'
  }
];

const page = document.body.dataset.page || 'home';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const car = (id) => CARS.find((x) => x.id === id) || CARS[0];
const link = (name, url) => `<a href="${url}" class="${page === name.toLowerCase() ? 'active' : ''}">${name}</a>`;
const actual = (id) => ['land-cruiser-v8', 'prado'].includes(id);

const rateHtml = (v, cls = 'rates') => v.rates
  ? `<div class="${cls}">${v.rates.map((r) => `<div class="rate-row"><span class="rate-label">${r.label}</span><span class="rate-range">${r.range}<small> / day</small></span>${r.note ? `<span class="rate-note">${r.note}</span>` : ''}</div>`).join('')}</div>`
  : `<div class="rate-single">${v.rate}</div>`;

function nav() {
  return `<header class="nav" id="nav"><div class="wrap nav-in"><a class="brand brand-logo" href="index.html"><img src="assets/logo.svg" alt="Depart Rides — Drive the Extraordinary" width="228" height="40"></a><nav class="links" id="links">${link('Home', 'index.html')}${link('Fleet', 'fleet.html')}${link('About', 'about.html')}${link('FAQ', 'faq.html')}${link('Contact', 'contact.html')}</nav><a class="nav-phone" href="${PHONE_TEL}" aria-label="Call Depart Rides on ${PHONE_DISPLAY}">☎ ${PHONE_DISPLAY}</a><a class="btn sm" href="booking.html">Book your ride ↗</a><button class="menu-btn" aria-label="Toggle navigation" aria-expanded="false" id="menu">☰ MENU</button></div></header>`;
}

function footer() {
  return `<footer class="footer"><div class="wrap"><div class="footer-main"><div><a href="index.html" class="brand brand-logo"><img src="assets/logo.svg" alt="Depart Rides — Drive the Extraordinary" width="273" height="48"></a><p style="max-width:350px;margin-top:25px">Car rentals in Jhelum: Toyota Land Cruiser V8, Toyota Prado, Haval H6, Jetour T2 and Toyota Corolla XLi.</p></div><div><h4>EXPLORE</h4><a href="fleet.html">Our Fleet</a><a href="booking.html">Book a Ride</a><a href="about.html">About Us</a><a href="faq.html">FAQs</a></div><div><h4>INFORMATION</h4><a href="contact.html">Contact</a><a href="terms.html">Rental Terms</a><a href="privacy.html">Privacy</a><a href="contact.html">Request a Quote</a></div><div><h4>CONTACT</h4><a href="${PHONE_TEL}">Call ${PHONE_DISPLAY}</a><a href="${wa()}" target="_blank" rel="noopener">WhatsApp us</a><span class="footer-loc">Jhelum, Pakistan</span></div></div><div class="footer-bottom"><span>© <span id="year"></span> Depart Rides. All rights reserved.</span><span>CRAFTED FOR THE JOURNEY.</span></div></div></footer><a class="wa-float" href="${page === 'vehicle' ? wa(bookText(car(new URLSearchParams(location.search).get('id')).name)) : wa()}" target="_blank" rel="noopener" aria-label="Chat with Depart Rides on WhatsApp">${WA_ICON}</a>`;
}

function heading(k, title, sub) {
  return `<section class="page-hero"><div class="wrap"><div class="eyebrow reveal">${k}</div><h1 class="reveal">${title}</h1><p class="reveal">${sub}</p></div></section>`;
}

function card(v, i = 0) {
  return `<article class="vehicle reveal delay${i % 3}" data-type="${v.type}"><a href="vehicle.html?id=${v.id}" class="vehicle-img"><img loading="lazy" src="${v.image}" alt="${v.name} — ${actual(v.id) ? 'actual Depart Rides vehicle' : 'illustrative photo of the model'}" onerror="this.style.opacity='.05'"><span class="badge">${actual(v.id) ? 'ACTUAL VEHICLE' : v.type.toUpperCase() + ' COLLECTION'}</span></a><div class="vehicle-body"><h3>${v.name}</h3><p>${v.tag}</p><div class="vehicle-meta"><span>${v.type}</span><span>${v.year}</span></div><div class="vehicle-bottom"><div><small>${v.rates ? 'RENTAL RATE · PKR PER DAY' : 'RENTAL RATE'}</small>${rateHtml(v)}</div><a href="vehicle.html?id=${v.id}" class="arrow" aria-label="Explore ${v.name}">↗</a></div></div></article>`;
}

function cards(list = CARS) {
  return list.map(card).join('');
}

function cta() {
  return `<section class="section tight"><div class="wrap"><div class="banner reveal"><div><h2>Your next drive<br>starts here.</h2><p>Tell us your dates, car and whether you are driving locally in Jhelum or out of city.</p></div><div class="banner-actions"><a class="btn dark" href="booking.html">Request your ride ↗</a><a class="btn dark" href="${PHONE_TEL}">Call ${PHONE_DISPLAY}</a><a class="btn dark" href="${wa()}" target="_blank" rel="noopener">${WA_ICON}WhatsApp</a></div></div></div></section>`;
}

function priceCards() {
  return CARS.map((v) => `<a class="price-card" href="vehicle.html?id=${v.id}"><span class="price-card__name">${v.name}</span><span class="price-card__tag">${v.tag}</span><span class="price-card__rate">${v.rates ? v.rates.map((r) => `<span>${r.label}: ${r.range}${r.note ? ` · ${r.note}` : ''}</span>`).join('') : v.rate}</span></a>`).join('');
}

function home() {
  return `<main>
<section class="cinema" id="cinema" aria-label="Cinematic introduction to Depart Rides">
  <div class="cinema-track">
    <div class="cinema-pin" id="cinema-pin">
      <div class="cinema-letterbox cinema-letterbox--top"></div>
      <div class="cinema-letterbox cinema-letterbox--bot"></div>
      <div class="cinema-stage" id="cinema-stage">
        <div class="cinema-layer cinema-bg"></div>
        <div class="cinema-layer cinema-film" data-layer="film"><canvas id="cinema-canvas" aria-label="Scroll-driven film: the Land Cruiser V8 door opens and the camera moves inside to the dashboard (illustrative AI-generated footage)"></canvas><p class="cinema-credit">Illustrative AI-generated footage of the Land Cruiser V8.</p></div>
        <div class="cinema-layer cinema-front" data-layer="front"><img src="assets/v8-front.jpg" alt="Land Cruiser V8 front, actual Depart Rides vehicle"></div>
        <div class="cinema-layer cinema-engine" data-layer="engine"><img src="assets/stock-engine.jpg" alt="Illustrative engine bay photograph"></div>
        <div class="cinema-vignette"></div>
        <div class="cinema-grade"></div>
      </div>
      <div class="cinema-ui">
        <div class="cinema-chapter" id="cinema-chapter">01  ·  ARRIVAL</div>
        <div class="cinema-progress" aria-hidden="true"><i id="cinema-progress"></i></div>
      </div>
      <div class="scene scene-hero" data-scene="hero">
        <div class="wrap">
          <span class="eyebrow">Car rentals · Jhelum, Pakistan</span>
          <h1><span class="line"><span>The road</span></span><span class="line"><span class="accent italic">is yours.</span></span></h1>
          <p class="intro">Five cars for Jhelum and beyond: Toyota Land Cruiser V8, Toyota Prado, Haval H6, Jetour T2 and Toyota Corolla XLi. Clear daily rates for local and outside-city trips.</p>
          <div class="hero-actions"><a class="btn" href="fleet.html">Explore the fleet ↗</a><a class="btn outline" href="booking.html">Book a ride</a></div>
        </div>
        <div class="scroll-hint">Scroll to enter the cabin <i></i></div>
      </div>
      <div class="scene scene-cabin" data-scene="cabin">
        <div class="wrap scene-cabin-grid">
          <div class="scene-copy">
            <span class="eyebrow">02 · The cabin</span>
            <h2>Quiet. Composed.<br><span class="accent italic">Considered.</span></h2>
            <p>From city errands in Jhelum to family trips out of town, choose the cabin that fits the day. Interior stills are illustrative stock images until photos of our own cars are available.</p>
          </div>
          <div class="lux-panels">
            <article class="lux-panel" data-panel="seats"><img src="assets/stock-seats.jpg" alt=""><div><span>01 / Family</span><h3>Room for seven</h3><p>The Toyota Prado seats seven for family journeys and group travel.</p></div></article>
            <article class="lux-panel" data-panel="cabin"><img src="assets/stock-cabin.jpg" alt=""><div><span>02 / Flagship</span><h3>Land Cruiser V8</h3><p>Our 2018 flagship for executive travel and special occasions.</p></div></article>
            <article class="lux-panel" data-panel="ride"><img src="assets/stock-interior.jpg" alt=""><div><span>03 / SUVs</span><h3>Haval H6 &amp; Jetour T2</h3><p>Modern five-seat SUVs for comfortable everyday and out-of-city trips.</p></div></article>
            <article class="lux-panel" data-panel="amenities"><img src="assets/stock-wheel.jpg" alt=""><div><span>04 / Sedan</span><h3>Corolla XLi</h3><p>A 2014 black Corolla XLi, 1.3L manual: simple, economical city driving.</p></div></article>
          </div>
        </div>
      </div>
      <div class="scene scene-perf" data-scene="perf">
        <div class="wrap scene-perf-inner">
          <div class="scene-copy">
            <span class="eyebrow">03 · Rates</span>
            <h2>Clear rates, <span class="accent italic">per day.</span></h2>
            <p>Our 2018 Land Cruiser V8, photographed on our own fleet. Local Jhelum rates include fuel for the V8, Prado and Haval H6; outside-city rates are without fuel.</p>
          </div>
          <div class="counters">
            <div class="counter"><strong><span data-count="5">00</span></strong><span>Cars in the fleet</span></div>
            <div class="counter"><strong><em>Rs </em><span data-count="20">00</span><em>K</em></strong><span>V8 per day from · local, with fuel</span></div>
            <div class="counter"><strong><em>Rs </em><span data-count="15">00</span><em>K</em></strong><span>Prado per day from · local, with fuel</span></div>
            <div class="counter"><strong><span data-count="2018">0000</span></strong><span>Flagship V8 year</span></div>
          </div>
          <p class="price-note">Daily rates in PKR for local Jhelum and outside-city trips, plus Islamabad &amp; Islamabad Airport rates (with fuel) for the Prado and Land Cruiser V8. Availability is confirmed on inquiry; Jetour T2 and Corolla XLi are <strong>Price on demand</strong>.</p>
          <div class="price-grid">${priceCards()}</div>
        </div>
      </div>
    </div>
  </div>
</section>
<div class="marquee"><div class="marquee-inner">DEPART RIDES ✦ CAR RENTALS IN JHELUM ✦ LAND CRUISER V8 ✦ PRADO ✦ HAVAL H6 ✦ JETOUR T2 ✦ COROLLA XLi ✦ DEPART RIDES ✦ CAR RENTALS IN JHELUM ✦ &nbsp;</div></div>
<section class="section" id="fleet">
  <div class="wrap">
    <div class="section-top">
      <div><span class="eyebrow reveal">04 · The collection</span><h2 class="reveal">Meet your <span class="accent italic">next ride.</span></h2></div>
      <p class="reveal">Five cars, from the Land Cruiser V8 to the Corolla XLi. Local Jhelum and outside-city rates on every priced car.</p>
    </div>
    <div class="grid grid-3">${cards()}</div>
    <div style="text-align:center;margin-top:35px"><a class="btn outline" href="fleet.html">View the entire fleet ↗</a></div>
  </div>
</section>
<section class="reel" aria-label="Fleet motion reel">
  <video src="assets/fleet-reel.mp4" poster="assets/fleet-reel-poster.jpg" autoplay muted loop playsinline></video>
  <div class="reel-copy"><div class="wrap"><span class="eyebrow">Our own cars</span><h2>The Depart Rides <span class="accent italic">fleet.</span></h2><p>Studio photographs of our Land Cruiser V8, Prado and Haval H6.</p></div></div>
</section>
${cta()}
</main>`;
}

function fleet() {
  return `<main>${heading('OUR FLEET', 'Choose your <span class="accent italic">ride.</span>', 'A curated collection for city drives, family adventures, executive travel and everything in between.')}<section class="section"><div class="wrap"><div class="filters" aria-label="Filter vehicles"><button class="chip selected" data-filter="All">All vehicles</button><button class="chip" data-filter="SUV">SUVs</button><button class="chip" data-filter="Luxury">Luxury</button><button class="chip" data-filter="Sedan">Sedans</button></div><div class="grid grid-3" id="fleet-grid">${cards()}</div><p class="fineprint">Note: Land Cruiser V8 and Prado photos show our actual vehicles; Haval H6 and Corolla XLi photos are illustrative photos of the model from Wikimedia Commons; Jetour T2 images are illustrative studio renders of the model. Photo credits: ${Object.keys(PHOTO_CREDITS).map(creditHtml).join('; ')}. Licences: <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a> / CC0. Rates shown are per day in PKR and are confirmed on inquiry; Jetour T2 and Corolla XLi are Price on demand.</p></div></section>${cta()}</main>`;
}

function vehicle() {
  const v = car(new URLSearchParams(location.search).get('id'));
  const imgs = v.gallery || [v.image];
  return `<main>${heading('THE COLLECTION', v.name, v.desc)}<section class="section"><div class="wrap detail-layout"><div class="reveal"><div class="detail-photo"><img id="main-car-image" src="${imgs[0]}" alt="${v.name}"></div><div class="detail-thumbs">${imgs.map((im, i) => `<img src="${im}" alt="${v.name} view ${i + 1}" data-gallery="${im}" tabindex="0">`).join('')}</div>${actual(v.id) ? '' : `<p class="fineprint">${PHOTO_CREDITS[v.id] ? 'Illustrative photos of this model from Wikimedia Commons: ' + creditHtml(v.id) + '.' : 'Illustrative studio renders of this model.'} Ask us for photographs of the actual car before booking.</p>`}</div><div class="panel reveal"><span class="eyebrow">Vehicle profile</span><h2 style="font-size:48px;margin:20px 0">${v.name}</h2><p>${v.desc}</p><div class="vehicle-meta" style="margin:26px 0"><span>${v.type}</span><span>${v.year}</span><span>${v.seats}</span>${(v.specs || []).map((x) => `<span>${x}</span>`).join('')}</div><div style="border-top:1px solid var(--line);padding-top:25px"><span style="font-size:12px;color:var(--muted);letter-spacing:.14em">${v.rates ? 'DAILY RATE · PKR' : 'DAILY RATE'}</span>${v.rates ? rateHtml(v, 'rates rates--lg') : `<h3 style="font-size:32px;margin:7px 0 23px">${v.rate}</h3>`}<a class="btn" href="booking.html?vehicle=${v.id}" style="width:100%">Request this vehicle ↗</a><div class="contact-actions"><a class="btn wa" href="${wa(bookText(v.name))}" target="_blank" rel="noopener">${WA_ICON}WhatsApp to book</a><a class="btn outline" href="${PHONE_TEL}">Call ${PHONE_DISPLAY}</a></div><p class="fineprint">Availability, pricing, driver options and rental terms are confirmed by our team. Listed rates are indicative daily ranges in PKR.</p></div></div></div></section><section class="section tight dark-block"><div class="wrap"><span class="eyebrow">Explore more</span><h2 style="margin:20px 0 40px">More ways to <span class="accent italic">move.</span></h2><div class="grid grid-3">${cards(CARS.filter((x) => x.id !== v.id).slice(0, 3))}</div></div></section></main>`;
}

function booking() {
  const pre = new URLSearchParams(location.search).get('vehicle') || '';
  return `<main>${heading('BOOK YOUR JOURNEY', 'Let’s get <span class="accent italic">moving.</span>', 'Tell us where, when and what you’d love to drive. Send an inquiry in just a few steps.')}<section class="section"><div class="wrap detail-layout"><div class="panel reveal"><h3>Request a reservation</h3><p>We’ll prepare your inquiry. Sending an inquiry does not reserve a car or take any payment.</p><form id="booking-form" class="form two"><label>Full name *<input required name="name" placeholder="Your full name" maxlength="100"></label><label>Email *<input required type="email" name="email" placeholder="you@example.com"></label><label>Phone / WhatsApp *<input required name="phone" placeholder="+92 ..."></label><label>Preferred vehicle *<select name="vehicle" required><option value="">Select a vehicle</option>${CARS.map((v) => `<option value="${v.id}" ${pre === v.id ? 'selected' : ''}>${v.name}</option>`).join('')}</select></label><label>Pickup date *<input required name="pickup" type="date" id="pickup-date"></label><label>Return date *<input required name="return" type="date" id="return-date"></label><label class="full">Pickup location *<input required name="location" placeholder="City / pickup point"></label><label class="full">Your message (optional)<textarea name="message" placeholder="Driver requirements, itinerary, additional questions..."></textarea></label><div class="full" id="form-feedback" role="status"></div><button class="btn full" type="submit">Prepare booking inquiry ↗</button></form></div><div class="reveal"><div class="feature"><span class="num">HOW IT WORKS</span><h3>01. Select your ride</h3><p>Pick from our SUVs, the Land Cruiser V8 or the Corolla XLi sedan.</p><h3>02. Share your details</h3><p>Enter your travel dates, location and contact information.</p><h3>03. Confirm directly</h3><p>Review your inquiry and send it through your own email app. Final booking requires confirmation from Depart Rides.</p></div><p class="fineprint">No payment is collected on this website. Payment and any deposit are arranged directly with Depart Rides once your booking is confirmed.</p></div></div></section></main>`;
}

function about() {
  return `<main>${heading('OUR STORY', 'Built for <span class="accent italic">the drive.</span>', 'A simple idea: every journey deserves a vehicle that feels right.')}<section class="section"><div class="wrap detail-layout"><div class="reveal"><span class="eyebrow">Who we are</span><h2 style="margin-top:25px">The journey<br>is the <span class="accent italic">point.</span></h2><p>Depart Rides is a car rental brand focused on making it easier to find the right vehicle for your plans. Our fleet is the Toyota Land Cruiser V8, Toyota Prado, Haval H6, Jetour T2 and Toyota Corolla XLi.</p><p>We believe the rental experience should feel considered, clear and personal—from the first inquiry to the final handover.</p><a class="btn" href="fleet.html">Meet the fleet ↗</a></div><div class="detail-photo reveal"><img src="assets/land-cruiser-front.jpg" alt="Actual Depart Rides Land Cruiser V8"></div></div></section><section class="section dark-block"><div class="wrap"><span class="eyebrow">Our approach</span><div class="grid grid-3" style="margin-top:30px"><div class="feature reveal"><span class="num">01</span><h3>Choice</h3><p>A thoughtfully selected range of vehicles for different travel needs.</p></div><div class="feature reveal delay1"><span class="num">02</span><h3>Clarity</h3><p>Transparent inquiry-based pricing and terms confirmed before your trip.</p></div><div class="feature reveal delay2"><span class="num">03</span><h3>Experience</h3><p>Attention to the details that make each journey easier.</p></div></div></div></section>${cta()}</main>`;
}

function faq() {
  const data = [
    ['How do I book a car?', 'Browse the fleet, choose a vehicle and submit a booking inquiry with your dates and pickup location. A booking is only confirmed after direct communication with Depart Rides.'],
    ['Are prices listed online?', 'Daily rate ranges in PKR are listed for the Toyota Prado, Haval H6 and Land Cruiser V8, for local Jhelum and outside-city trips. The Prado (Rs 27,000 – 30,000) and Land Cruiser V8 (Rs 35,000 – 40,000) also have daily rates with fuel for Islamabad and Islamabad Airport trips. The Jetour T2 and Corolla XLi are Price on demand. Final rates depend on dates, trip duration and requirements and are confirmed on inquiry.'],
    ['Can I request a driver?', 'Yes, you can mention your driver requirements in the booking inquiry. Availability and any additional charges must be confirmed directly.'],
    ['What documents do I need?', 'Required identification, license and security arrangements depend on the rental type and will be confirmed before booking.'],
    ['Can I change or cancel a booking?', 'Please contact Depart Rides directly. Cancellation and modification conditions will be explained when your booking is confirmed.'],
    ['Are the photos of the actual cars?', 'The Toyota Land Cruiser V8 and Toyota Prado photographs are of actual vehicles supplied by Depart Rides. Photos of the Haval H6 and Corolla XLi are illustrative photos of each model from Wikimedia Commons; Jetour T2 images are illustrative studio renders of a white T2. Interior and engine stills on the home page are illustrative stock images.'],
    ['Is my reservation confirmed after I submit the form?', 'No. The form prepares an inquiry only. Our team confirms availability and your booking directly.']
  ];
  return `<main>${heading('GOOD TO KNOW', 'Your questions. <span class="accent italic">Answered.</span>', 'Everything you need to know before setting off.')}<section class="section"><div class="wrap text-content">${data.map(([q, a], i) => `<details class="faq-item reveal" ${i === 0 ? 'open' : ''}><summary>${q}</summary><p>${a}</p></details>`).join('')}</div></section>${cta()}</main>`;
}

function contact() {
  return `<main>${heading('GET IN TOUCH', 'Let’s <span class="accent italic">talk rides.</span>', 'Have a question or a specific itinerary in mind? Send us a message.')}<section class="section"><div class="wrap detail-layout"><div class="panel reveal"><h3>Send an inquiry</h3><form class="form" id="contact-form"><label>Your name *<input name="name" required placeholder="Full name"></label><label>Email address *<input name="email" type="email" required placeholder="you@example.com"></label><label>Phone / WhatsApp<input name="phone" placeholder="+92 ..."></label><label>Message *<textarea name="message" required placeholder="How can we help?"></textarea></label><div id="form-feedback" role="status"></div><button class="btn" type="submit">Prepare message ↗</button></form></div><div class="reveal"><span class="eyebrow">We're here to help</span><h2 style="margin-top:20px">Start a<br><span class="accent italic">conversation.</span></h2><p>Ask about availability, rental options, trip requirements or a custom quote.</p><div class="feature" style="margin-top:35px"><h3>Contact details</h3><p>Phone / WhatsApp: <a href="${PHONE_TEL}">${PHONE_DISPLAY}</a> (+92 339 9999038)<br>Location: Jhelum, Pakistan</p><div class="contact-actions"><a class="btn wa" href="${wa()}" target="_blank" rel="noopener">${WA_ICON}WhatsApp us</a><a class="btn outline" href="${PHONE_TEL}">Call now</a><a class="btn outline" href="booking.html">Booking inquiry ↗</a></div></div></div></div></section></main>`;
}

function legal(which) {
  const terms = which === 'terms';
  return `<main>${heading(terms ? 'RENTAL INFORMATION' : 'YOUR INFORMATION', terms ? 'Rental <span class="accent italic">terms.</span>' : 'Privacy <span class="accent italic">notice.</span>', terms ? 'Important information to review before confirming a vehicle rental.' : 'How information you enter on this website is handled.')}<section class="section"><div class="wrap text-content reveal">${terms ? `<h2>Reservation process</h2><p>Website inquiries do not constitute a confirmed reservation. Vehicle availability, pickup and return locations, rental charges, driver arrangements and all other terms must be confirmed directly with Depart Rides.</p><h2>Pricing and payments</h2><p>Indicative daily rates are listed on the fleet pages; final pricing is confirmed on inquiry. No payment is collected through this website. Any deposit, payment method or refund policy must be agreed directly before rental.</p><h2>Documents and responsibilities</h2><p>Identity verification, driving license requirements, permitted use, insurance, fuel, mileage, damage, traffic violations and cancellation terms will be set out in the final rental agreement.</p><h2>Important</h2><p>This page is general guidance, not a binding rental contract. The full terms are set out in the rental agreement provided when your booking is confirmed.</p>` : `<h2>Information you provide</h2><p>The booking and contact forms collect information that you choose to enter, such as your name, email address, phone number, travel dates and inquiry details.</p><h2>How the forms work</h2><p>This website does not send form data to a server or store it in a database. Submitting a form prepares an email using your device's email application. The message is sent only if you choose to send it.</p><h2>Third-party resources</h2><p>Animation libraries (GSAP) and web fonts load from external providers. Those providers may receive standard connection information when your browser requests their assets.</p><h2>Questions</h2><p>For any question about your information, contact Depart Rides through the contact page.</p>`}</div></section></main>`;
}

const routes = {
  home, fleet, vehicle, booking, about, faq, contact,
  terms: () => legal('terms'),
  privacy: () => legal('privacy')
};

$('#app').innerHTML = nav() + (routes[page] || home)() + footer();
document.title = `${({
  home: 'Car Rentals in Jhelum',
  fleet: 'Our Fleet',
  vehicle: car(new URLSearchParams(location.search).get('id')).name,
  booking: 'Book a Ride',
  about: 'About Us',
  faq: 'FAQs',
  contact: 'Contact',
  terms: 'Rental Terms',
  privacy: 'Privacy'
})[page] || 'Car Rentals'} | Depart Rides`;
if (page === 'vehicle') { const vv = car(new URLSearchParams(location.search).get('id')); const md = document.querySelector('meta[name="description"]'); const cu = `https://departrides.com/vehicle.html?id=${vv.id}`; document.querySelectorAll('link[rel="canonical"],meta[property="og:url"]').forEach((el) => { el.setAttribute(el.tagName === 'LINK' ? 'href' : 'content', cu); }); const ogi = document.querySelector('meta[property="og:image"]'); if (ogi) ogi.content = `https://departrides.com/${vv.image}`; if (md) md.content = `${vv.name} for rent in Jhelum from Depart Rides. ${vv.rates ? vv.rates.map((r) => `${r.label}: ${r.range} per day${r.note ? ` (${r.note.toLowerCase()})` : ''}`).join('; ') + '.' : vv.rate + '.'}`; }
$('#year').textContent = new Date().getFullYear();

const navEl = $('#nav');
function onScroll() {
  navEl.classList.toggle('scrolled', scrollY > 30);
}
addEventListener('scroll', onScroll, { passive: true });
onScroll();

$('#menu').onclick = () => {
  const open = $('#links').classList.toggle('open');
  $('#menu').setAttribute('aria-expanded', String(open));
};

const obs = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      obs.unobserve(e.target);
    }
  });
}, { threshold: 0.07, rootMargin: '0px 0px -20px 0px' });
$$('.reveal').forEach((e) => obs.observe(e));

$$('[data-filter]').forEach((b) => b.addEventListener('click', () => {
  $$('[data-filter]').forEach((x) => x.classList.remove('selected'));
  b.classList.add('selected');
  $$('.vehicle').forEach((x) => {
    x.classList.toggle('hidden', b.dataset.filter !== 'All' && x.dataset.type !== b.dataset.filter);
  });
}));

$$('[data-gallery]').forEach((x) => {
  const fn = () => { $('#main-car-image').src = x.dataset.gallery; };
  x.onclick = fn;
  x.onkeydown = (e) => { if (e.key === 'Enter') fn(); };
});

const date = new Date();
date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
const today = date.toISOString().slice(0, 10);
if ($('#pickup-date')) {
  $('#pickup-date').min = today;
  $('#return-date').min = today;
  $('#pickup-date').onchange = () => {
    $('#return-date').min = $('#pickup-date').value;
    if ($('#return-date').value < $('#pickup-date').value) $('#return-date').value = $('#pickup-date').value;
  };
}

function sendForm(form, kind) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const v = Object.fromEntries(new FormData(form).entries());
    const out = $('#form-feedback');
    if (kind === 'booking' && v.return < v.pickup) {
      out.innerHTML = '<p class="error">Return date cannot be before pickup date.</p>';
      return;
    }
    const subject = kind === 'booking' ? `Depart Rides booking inquiry — ${car(v.vehicle).name}` : 'Depart Rides contact inquiry';
    const lines = Object.entries(v).map(([k, value]) => `${k.toUpperCase()}: ${k === 'vehicle' ? car(value).name : value}`).join('\n');
    const body = `Hello Depart Rides,\n\n${kind === 'booking' ? 'I would like to request a vehicle booking.' : 'I would like to contact you.'}\n\n${lines}\n\nPlease confirm the next steps.\n`;
    out.innerHTML = '<p class="notice">Your inquiry is ready. Your email app will open so you can address and send it. No booking is confirmed yet.</p>';
    location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });
}
if ($('#booking-form')) sendForm($('#booking-form'), 'booking');
if ($('#contact-form')) sendForm($('#contact-form'), 'contact');
