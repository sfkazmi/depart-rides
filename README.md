# Depart Rides — Complete Static Website

Open `index.html` in a modern browser or serve the folder with `python -m http.server 8000`.

Live: https://sfkazmi.github.io/depart-rides/

## Pages
Home, Fleet, Vehicle Detail (dynamic query parameter), Booking Inquiry, About, FAQ, Contact, Rental Terms, Privacy.

## Actual fleet
Toyota Prado 2024, Haval H6 2025, Jetour T2 2026, Toyota Corolla XLi 2014 (black), Toyota Land Cruiser V8 2018.

## Pricing
No numeric rental rates exist in the original site data. Every vehicle is labelled **On request** (the copy already used on fleet and vehicle pages). The cinematic home “pricing” strip uses that same label — it does not invent prices.

Performance counters on the home sequence use facts already on the site: 5 fleet vehicles, Prado 7 seats, 24/7 inquiry, 2018 flagship V8 year.

## Images
The Land Cruiser V8 and Prado photographs in `assets/` are real images provided by the business. Haval H6 and Corolla XLi images are freely licensed illustrative photos of each model from Wikimedia Commons (see credits below; Jetour T2 images are illustrative studio renders), stored locally in `assets/`. Replace them with photos of the actual cars when available.

### Stock interior and engine stills
Cabin and engine photography of the actual fleet does not exist in `assets/`. The home sequence uses downloaded, free-license stills (illustrative only — not Depart Rides vehicles):

| File | Source | Credit |
| --- | --- | --- |
| `assets/stock-cabin.jpg` | [Unsplash](https://unsplash.com/photos/nmI1lNdv_jg) | Bram Van Oost (`@ort`) — Hongqi E-HS9 cabin |
| `assets/stock-seats.jpg` | [Unsplash](https://unsplash.com/photos/aKTAKvDnPcc) | Vadym Kudriavtsev (`@clipnjoy`) — quilted leather seat |
| `assets/stock-interior.jpg` | [Unsplash](https://unsplash.com/photos/JFZNAg-elAI) | Titi Iaru (`@titi_iaru`) — Aston Martin cabin |
| `assets/stock-leather.jpg` | [Unsplash](https://unsplash.com/photos/gXaWrl4eQ0c) | Christopher Lam (`@cwdlphotos`) — Porsche cabin |
| `assets/stock-wheel.jpg` | [Unsplash](https://unsplash.com/photos/FZcQRwFSR1Y) | Leiada Krözjhen (`@leiadakrozjhen`) — tan luxury cabin |
| `assets/stock-engine.jpg` | [Unsplash](https://unsplash.com/photos/D4YRzVtynV8) | engine bay still (`photo-1486262715619-67b85e0b08d3`) |

Unsplash License / Pexels License: free to use, with photographer credit.

## Forms
Booking and contact forms are functional client-side validation and create an email draft in the visitor's default email app. They DO NOT transmit data, create confirmed bookings, check live availability or take payments. Business phone/WhatsApp: 0339 9999038 (+92 339 9999038), shown in the header, footer, contact page, home banner, vehicle pages (WhatsApp prefilled with the car name) and as a floating WhatsApp button on mobile; schema.org AutoRental JSON-LD is in every page head. A production deployment could add a business email, backend or form service, privacy and legal review, real rental pricing and terms.

## Animation
The home page is a pinned, scroll-driven cinematic sequence (GSAP + ScrollTrigger via jsDelivr CDN): the Land Cruiser drives into frame, the camera zooms into an interior, then pulls back to the front/engine with animated counters and on-request pricing, then fleet, motion reel, booking CTA and footer. Other pages share the dark luxury palette, serif display type, and reveal-on-scroll. `prefers-reduced-motion` disables pin/tween and shows stacked static scenes. No build step.

## Customization
Edit fleet details in `assets/app.js` under `CARS`, cinematic motion in `assets/cinematic.js`, and visual styles in `assets/style.css`.

## Newly provided media
- Haval H6: owner-supplied studio rear photo `assets/haval-h6-rear.jpg` (in its gallery and the reel).
- Toyota Prado: three actual photos in assets/prado-*.jpg, included in its vehicle gallery.
- Home page motion reel: `assets/fleet-reel.mp4` (+ `fleet-reel-poster.jpg`), built with ffmpeg (Ken Burns zooms/pans, crossfades) from the business's own studio photos `land-cruiser-*`, `prado-*`, `v8-*` and `haval-h6-rear.jpg`. 1920x1080, ~20s, H.264, no audio. Replaces the former GWM video, which was removed because it showed bystanders.

### Home scroll film (door → cabin → dashboard)
The home hero is a scroll-scrubbed film drawn on a `<canvas>` from a WebP frame sequence (`assets/seq/d/` 1280px for desktop, `assets/seq/m/` 720px for phones, 100 frames each) for reliable scrubbing on iOS Safari. The footage is an AI-generated (Grok Imagine) illustrative clip of the V8's door opening and the camera moving in to the dashboard; poster `assets/v8-video-poster.webp` is used for reduced-motion. On phones the rates/perf block follows the film as a normal section.

Earlier still frames: `assets/v8-door-0.webp` (door closed), `v8-door-1.webp` (door open) and `v8-door-2.webp` (view through the open door) are AI-generated illustrative renders of the Land Cruiser V8 in the site's studio style. `assets/v8-dashboard.webp` is a real Wikimedia Commons photo of a first-facelift (2012) Land Cruiser J200 V8 dashboard (credited below and on the home page), cropped to a wide strip that pans with a perspective rotate on scroll.

## Wikimedia Commons photo credits
Shown on the site (fleet page note and each vehicle page). Images were resized/cropped.

| File | Source | Author | License |
|---|---|---|---|
| `assets/haval-h6-front.jpg` | [File:Haval_H6_III_007.jpg](https://commons.wikimedia.org/wiki/File:Haval_H6_III_007.jpg) | Jengtingchen | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `assets/v8-dashboard.webp` | [File:2023 Manila Auto Salon - 2012 Toyota Land Cruiser J200 ZX V8 by Atoy Customs (interior).jpg](https://commons.wikimedia.org/wiki/File:2023_Manila_Auto_Salon_-_2012_Toyota_Land_Cruiser_J200_ZX_V8_by_Atoy_Customs_(interior).jpg) | Ethan Llamas | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `assets/corolla-xli-front.jpg` | [File:Toyota_Altis_2.0_V_(Attitude_Black).jpg](https://commons.wikimedia.org/wiki/File:Toyota_Altis_2.0_V_(Attitude_Black).jpg) | Captainmorlypogi1959 | CC BY-SA 4.0 |

## Analytics

GA4 is wired in `assets/analytics.js`. Set `GA_ID` to your Measurement ID (G-XXXXXXXXXX) to activate it; while it is empty nothing loads. Events: `whatsapp_click` (car_name), `call_click`, `vehicle_view` (car_id, car_name).

Short links (Apache vhost, 302): /go/status, /go/wa-fb, /go/wa-group. Opens are counted by `/root/departrides-stats.sh` on the server.
